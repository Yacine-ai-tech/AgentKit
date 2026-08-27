"""Declarative tool packs — define MCP tools in YAML instead of Python.

AgentKit's built-in tools happen to be business-KPI tools, but nothing about the server
is bound to that domain. A *tool pack* is a YAML file describing tools over a data
source; loading one registers real MCP tools with real schemas and real policy. Adding a
tool to your own deployment means writing YAML, not forking this repo:

    name: support
    description: Helpdesk tools
    datasource:
      type: postgres            # postgres | http
      url_env: SUPPORT_DB_URL   # named env var — never an inline credential
    tools:
      - name: open_tickets
        description: List open tickets for a queue.
        effect: read
        params:
          - {name: queue, type: string, required: true}
          - {name: limit, type: integer, required: false, default: 50}
        query: >
          SELECT id, subject, priority FROM tickets
          WHERE queue = %(queue)s AND status = 'open'
          ORDER BY priority DESC LIMIT %(limit)s

      - name: escalate_ticket
        description: Raise a ticket's priority.
        effect: write                       # gated by AGENTKIT_ALLOW_WRITES
        scopes: [support.write]             # gated by AGENTKIT_SCOPES
        params:
          - {name: ticket_id, type: integer, required: true}
        statement: UPDATE tickets SET priority = 'high' WHERE id = %(ticket_id)s

Design constraints that make this safe to expose to a model:

* **Parameters are always bound, never interpolated.** `:name` placeholders go through
  the driver's parameter binding, so a model-supplied value cannot alter SQL structure.
  Pack authors write the query; the agent only fills declared parameters.
* **Effects are declared, not inferred.** `read`/`write`/`destructive` drive the policy
  engine (see core/policy.py). A pack cannot grant itself more capability than the
  operator has enabled.
* **Credentials come from named env vars.** A pack file is safe to commit and share.
* **Writes support dry-run.** A `write`/`destructive` tool called with dry_run=true
  reports what it would affect without committing.

Packs load from AGENTKIT_PACKS (a comma-separated list of .yaml files or directories),
defaulting to the bundled `packs/` directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentkit_mcp.core.logger import get_logger
from agentkit_mcp.core.policy import DESTRUCTIVE, READ, WRITE, ToolPolicy, policy_engine

log = get_logger(__name__)

try:
    import yaml

    _YAML = True
except ImportError:  # pragma: no cover
    _YAML = False
    log.warning(
        "pyyaml not installed — declarative tool packs unavailable (pip install pyyaml)"
    )

_TYPES = {"string": str, "integer": int, "number": float, "boolean": bool}
DEFAULT_PACK_DIR = Path(__file__).resolve().parent.parent.parent / "packs"


@dataclass
class PackParam:
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""

    def coerce(self, value: Any) -> Any:
        if value is None:
            return None
        py = _TYPES.get(self.type, str)
        if py is bool and isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        try:
            return py(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"parameter {self.name!r} expects {self.type}, got {value!r}"
            ) from e

    def to_meta(self) -> Dict[str, Any]:
        m = {"name": self.name, "type": self.type, "required": self.required}
        if self.default is not None:
            m["default"] = self.default
        if self.description:
            m["description"] = self.description
        return m


@dataclass
class PackTool:
    name: str
    description: str
    effect: str = READ
    scopes: List[str] = field(default_factory=list)
    params: List[PackParam] = field(default_factory=list)
    query: Optional[str] = None  # read
    statement: Optional[str] = None  # write / destructive
    request: Optional[Dict[str, Any]] = None  # http datasource
    rate_limit: Optional[int] = None
    requires_approval: Optional[bool] = None
    pack: str = ""

    @property
    def sql(self) -> Optional[str]:
        return self.query or self.statement

    def bind(self, supplied: Dict[str, Any]) -> Dict[str, Any]:
        """Validate + coerce caller args into bindable parameters."""
        out: Dict[str, Any] = {}
        for p in self.params:
            if p.name in supplied and supplied[p.name] is not None:
                out[p.name] = p.coerce(supplied[p.name])
            elif p.default is not None:
                out[p.name] = p.coerce(p.default)
            elif p.required:
                raise ValueError(f"missing required parameter {p.name!r}")
            else:
                out[p.name] = None
        unknown = (
            set(supplied or {})
            - {p.name for p in self.params}
            - {"dry_run", "approval_token"}
        )
        if unknown:
            raise ValueError(f"unknown parameter(s): {sorted(unknown)}")
        return out

    def to_meta(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "params": [p.to_meta() for p in self.params],
            "endpoint": f"/api/packs/{self.pack}/{self.name}",
            "effect": self.effect,
            "scopes": self.scopes,
            "pack": self.pack,
        }


@dataclass
class ToolPack:
    name: str
    description: str
    datasource: Dict[str, Any]
    tools: List[PackTool]
    source_file: str = ""

    @property
    def datasource_type(self) -> str:
        return (self.datasource or {}).get("type", "postgres")

    def resolve_url(self) -> str:
        """Read the datasource URL from its named env var (never inline in the pack)."""
        ds = self.datasource or {}
        env_name = ds.get("url_env")
        if env_name:
            url = os.getenv(env_name, "")
            if not url:
                raise RuntimeError(
                    f"pack {self.name!r}: datasource env var {env_name!r} is not set"
                )
            return url
        if ds.get("url"):
            return ds["url"]
        raise RuntimeError(
            f"pack {self.name!r}: datasource needs url_env (preferred) or url"
        )


def _parse_tool(raw: Dict[str, Any], pack_name: str) -> PackTool:
    name = raw.get("name")
    if not name:
        raise ValueError(f"pack {pack_name!r}: a tool is missing 'name'")
    effect = (raw.get("effect") or READ).lower()
    if effect not in (READ, WRITE, DESTRUCTIVE):
        raise ValueError(
            f"tool {name!r}: effect must be read|write|destructive, got {effect!r}"
        )
    if effect == READ and raw.get("statement"):
        raise ValueError(
            f"tool {name!r}: uses 'statement' but declares effect=read — "
            "use 'query' for reads, or declare a mutating effect"
        )
    params = [
        PackParam(
            name=p["name"],
            type=p.get("type", "string"),
            required=bool(p.get("required")),
            default=p.get("default"),
            description=p.get("description", ""),
        )
        for p in raw.get("params", []) or []
    ]
    tool = PackTool(
        name=name,
        description=raw.get("description", ""),
        effect=effect,
        scopes=list(raw.get("scopes", []) or []),
        params=params,
        query=raw.get("query"),
        statement=raw.get("statement"),
        request=raw.get("request"),
        rate_limit=raw.get("rate_limit"),
        requires_approval=raw.get("requires_approval"),
        pack=pack_name,
    )
    if not (tool.sql or tool.request):
        raise ValueError(
            f"tool {name!r}: needs one of 'query', 'statement', or 'request'"
        )
    return tool


def load_pack_file(path: Path) -> ToolPack:
    if not _YAML:
        raise RuntimeError("pyyaml is required to load tool packs")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    name = raw.get("name") or path.stem
    tools = [_parse_tool(t, name) for t in raw.get("tools", []) or []]
    pack = ToolPack(
        name=name,
        description=raw.get("description", ""),
        datasource=raw.get("datasource", {}) or {},
        tools=tools,
        source_file=str(path),
    )
    return pack


def discover_pack_files() -> List[Path]:
    spec = os.getenv("AGENTKIT_PACKS", "").strip()
    roots = (
        [Path(p.strip()) for p in spec.split(",") if p.strip()]
        if spec
        else [DEFAULT_PACK_DIR]
    )
    files: List[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml")))
        elif root.is_file():
            files.append(root)
        else:
            log.warning("tool pack path not found: %s", root)
    return files


def load_packs() -> Dict[str, ToolPack]:
    """Load every configured pack and register each tool's policy.

    A malformed pack is skipped with a logged error rather than taking the server down —
    one bad third-party pack shouldn't stop the rest of the deployment from serving.
    """
    packs: Dict[str, ToolPack] = {}
    if not _YAML:
        return packs
    for path in discover_pack_files():
        try:
            pack = load_pack_file(path)
        except Exception as e:
            log.error("failed to load tool pack %s: %s", path, e)
            continue
        packs[pack.name] = pack
        for tool in pack.tools:
            policy_engine.register(
                ToolPolicy(
                    name=tool.name,
                    effect=tool.effect,
                    scopes=tuple(tool.scopes),
                    rate_limit=tool.rate_limit,
                    requires_approval=tool.requires_approval,
                    description=tool.description,
                )
            )
        log.info(
            "loaded tool pack %r (%d tools) from %s",
            pack.name,
            len(pack.tools),
            path.name,
        )
    return packs
