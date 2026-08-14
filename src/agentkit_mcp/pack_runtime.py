"""Executes declarative tool-pack tools under policy enforcement.

Single funnel for every pack tool call, whatever the caller (MCP client, REST facade,
LangGraph node, CrewAI agent). The order is always:

    policy check -> audit(pending) -> execute (or simulate) -> audit(outcome)

so an action is never taken without a decision recorded first, and the record exists
even when execution then crashes.
"""
from __future__ import annotations

import inspect
import time
from typing import Any, Dict, List, Optional

import anyio

from agentkit_mcp.core.logger import get_logger
from agentkit_mcp.core.policy import READ, PolicyDenied, policy_engine
from agentkit_mcp.toolpacks import PackTool, ToolPack

log = get_logger(__name__)

_PY_TYPES = {"string": str, "integer": int, "number": float, "boolean": bool}


def _rows_to_records(cur, limit: int = 500):
    rows = cur.fetchmany(limit)
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return [dict(r) for r in rows]
    cols = [d[0] for d in (cur.description or [])]
    return [dict(zip(cols, r)) for r in rows]


def _run_sql(pack: ToolPack, tool: PackTool, bound: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    """Blocking DB work — always called via a worker thread, never on the event loop."""
    import psycopg
    from psycopg.rows import dict_row

    url = pack.resolve_url()
    sql = tool.sql

    with psycopg.connect(url, row_factory=dict_row, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            if tool.effect == READ:
                cur.execute(sql, bound)
                return {"rows": _rows_to_records(cur), "effect": READ}

            # Mutating path. dry_run runs the statement inside a transaction that is
            # always rolled back, so the caller learns the true affected-row count from
            # the real database without committing anything.
            cur.execute(sql, bound)
            affected = cur.rowcount
            if dry_run:
                conn.rollback()
                return {"dry_run": True, "would_affect_rows": affected, "committed": False,
                        "effect": tool.effect}
            conn.commit()
            return {"affected_rows": affected, "committed": True, "effect": tool.effect}


async def _run_http(pack: ToolPack, tool: PackTool, bound: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    import httpx

    req = tool.request or {}
    base = pack.resolve_url().rstrip("/")
    path = str(req.get("path", "/")).format(**{k: ("" if v is None else v) for k, v in bound.items()})
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    method = str(req.get("method", "GET")).upper()

    if dry_run and tool.effect != READ:
        return {"dry_run": True, "committed": False, "would_call": {"method": method, "url": url},
                "effect": tool.effect}

    headers = dict(req.get("headers", {}) or {})
    for k, v in list(headers.items()):
        if isinstance(v, str) and v.startswith("$"):   # $ENV_VAR indirection, never inline secrets
            import os
            headers[k] = os.getenv(v[1:], "")

    params = {k: v for k, v in bound.items() if v is not None} if method == "GET" else None
    json_body = {k: v for k, v in bound.items() if v is not None} if method != "GET" else None

    async with httpx.AsyncClient(timeout=req.get("timeout", 30)) as client:
        resp = await client.request(method, url, params=params, json=json_body, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"http_{resp.status_code}: {resp.text[:300]}")
    try:
        return {"result": resp.json(), "effect": tool.effect}
    except Exception:
        return {"result": resp.text[:5000], "effect": tool.effect}


async def call_pack_tool(
    pack: ToolPack,
    tool: PackTool,
    args: Optional[Dict[str, Any]] = None,
    *,
    caller: str = "mcp",
    caller_scopes: Optional[set] = None,
) -> Dict[str, Any]:
    """Run one pack tool end-to-end under policy. Raises PolicyDenied if refused."""
    args = dict(args or {})
    dry_run = bool(args.pop("dry_run", False))
    approval_token = args.pop("approval_token", None)

    decision = policy_engine.check(
        tool.name, args=args, caller_scopes=caller_scopes,
        approval_token=approval_token, dry_run=dry_run,
    )
    record = policy_engine.record(tool.name, decision, args=args, caller=caller)
    if not decision.allowed:
        raise PolicyDenied(decision.reason)

    t0 = time.time()
    try:
        bound = tool.bind(args)
        if tool.request:
            result = await _run_http(pack, tool, bound, dry_run)
        else:
            result = await anyio.to_thread.run_sync(_run_sql, pack, tool, bound, dry_run)
    except PolicyDenied:
        raise
    except Exception as e:
        policy_engine.complete(record, outcome="error", error=str(e),
                               duration_ms=round((time.time() - t0) * 1000, 1))
        log.exception("pack tool %s.%s failed: %s", pack.name, tool.name, e)
        return {"error": str(e), "tool": tool.name, "pack": pack.name}

    policy_engine.complete(record, outcome="ok",
                           duration_ms=round((time.time() - t0) * 1000, 1))
    result.setdefault("tool", tool.name)
    result.setdefault("pack", pack.name)
    result["audit_id"] = record.id
    return result


def _make_tool_callable(pack: ToolPack, tool: PackTool):
    """Synthesize an async function whose signature mirrors the YAML params.

    FastMCP derives each tool's JSON Schema by introspecting the callable, so a
    YAML-declared tool has to present a real typed signature rather than **kwargs —
    otherwise every pack tool would advertise an empty schema to the model.
    """
    async def _run(**kwargs: Any) -> Dict[str, Any]:
        try:
            return await call_pack_tool(pack, tool, kwargs, caller="mcp")
        except PolicyDenied as e:
            # Surface refusals to the model as a normal result, so it can explain the
            # block to the user instead of the client seeing an opaque transport error.
            return {"error": "policy_denied", "detail": str(e), "tool": tool.name}

    params: List[inspect.Parameter] = []
    annotations: Dict[str, Any] = {}
    for p in tool.params:
        py = _PY_TYPES.get(p.type, str)
        if p.required and p.default is None:
            ann, default = py, inspect.Parameter.empty
        else:
            ann, default = Optional[py], p.default
        params.append(inspect.Parameter(
            p.name, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=ann))
        annotations[p.name] = ann

    if tool.effect != READ:
        params.append(inspect.Parameter(
            "dry_run", inspect.Parameter.KEYWORD_ONLY, default=False, annotation=bool))
        annotations["dry_run"] = bool
        policy = policy_engine.get(tool.name)
        if policy is not None and policy.approval_required:
            params.append(inspect.Parameter(
                "approval_token", inspect.Parameter.KEYWORD_ONLY,
                default=None, annotation=Optional[str]))
            annotations["approval_token"] = Optional[str]

    annotations["return"] = Dict[str, Any]
    _run.__signature__ = inspect.Signature(params)   # type: ignore[attr-defined]
    _run.__annotations__ = annotations
    _run.__name__ = tool.name

    doc = tool.description or f"{tool.name} ({pack.name} pack)"
    if tool.effect != READ:
        doc += (f"\n\nEffect: {tool.effect.upper()} — mutates data. "
                f"Pass dry_run=true to preview without committing.")
        p = policy_engine.get(tool.name)
        if p is not None and p.approval_required:
            doc += " Requires a human-supplied approval_token."
    _run.__doc__ = doc
    return _run


def register_pack_tools(mcp, packs: Dict[str, ToolPack]) -> List[str]:
    """Register every pack tool with the FastMCP server. Returns registered names."""
    registered: List[str] = []
    for pack in packs.values():
        for tool in pack.tools:
            try:
                mcp.tool()(_make_tool_callable(pack, tool))
                registered.append(tool.name)
            except Exception as e:
                log.error("could not register pack tool %s.%s: %s", pack.name, tool.name, e)
    if registered:
        log.info("registered %d declarative pack tool(s): %s", len(registered), ", ".join(registered))
    return registered
