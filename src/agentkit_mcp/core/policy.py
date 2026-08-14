"""Capability policy engine — the guardrail layer between an agent and any real effect.

The moment a tool server can *act* (not just read), "the model decided to" stops being an
acceptable audit trail. Every tool in AgentKit declares an effect class, and every
invocation is checked against policy before it runs and recorded after:

    read        no side effects; safe to call freely
    write       creates or modifies state (annotate a metric, open a ticket, post a note)
    destructive irreversible or externally-visible (delete, send email, pay, deploy)

Enforcement rules, in order:

  1. Unknown tool                  -> denied (nothing runs that wasn't declared)
  2. effect != read and writes are globally disabled  -> denied
     Writes are OFF unless AGENTKIT_ALLOW_WRITES=true. Fails closed: a default install
     exposed to the internet cannot mutate anything, no matter what the model asks.
  3. Caller lacks the tool's required scope           -> denied
  4. destructive without an approval token            -> denied (see below)
  5. Per-tool rate limit exceeded                     -> denied
  6. dry_run requested                                -> allowed, but the executor must
                                                         simulate rather than commit

Approval: a destructive tool needs `approval_token` matching AGENTKIT_APPROVAL_TOKEN.
That token is held by a human//supervising system, never given to the model — so an agent
can *propose* a destructive action and a human authorizes the specific call. This is the
human-in-the-loop gate, expressed as a capability rather than a UI prompt, which is what
lets it work identically for Claude Desktop, a REST caller, or an autonomous loop.

Everything above is deliberately independent of *which* agent framework is calling:
policy lives with the tool, not the client, so LangGraph / Claude Agent SDK / CrewAI /
a raw MCP client all get identical enforcement.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from agentkit_mcp.core.logger import get_logger

log = get_logger(__name__)

READ = "read"
WRITE = "write"
DESTRUCTIVE = "destructive"
EFFECTS = (READ, WRITE, DESTRUCTIVE)


def _env_true(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class ToolPolicy:
    """Declared capability envelope for a single tool."""
    name: str
    effect: str = READ
    scopes: tuple = ()             # caller must hold ALL of these
    rate_limit: Optional[int] = None   # max calls per window
    rate_window: int = 60
    requires_approval: Optional[bool] = None   # default: True iff destructive
    description: str = ""

    def __post_init__(self):
        if self.effect not in EFFECTS:
            raise ValueError(f"tool {self.name!r}: effect must be one of {EFFECTS}, got {self.effect!r}")

    @property
    def approval_required(self) -> bool:
        if self.requires_approval is not None:
            return self.requires_approval
        return self.effect == DESTRUCTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "effect": self.effect,
            "scopes": list(self.scopes),
            "rate_limit": self.rate_limit,
            "rate_window": self.rate_window,
            "requires_approval": self.approval_required,
            "description": self.description,
        }


@dataclass
class Decision:
    allowed: bool
    reason: str = ""
    dry_run: bool = False
    policy: Optional[ToolPolicy] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason, "dry_run": self.dry_run}


class PolicyDenied(PermissionError):
    """Raised when policy refuses an invocation. Message is safe to show a caller."""


@dataclass
class AuditRecord:
    id: str
    ts: str
    tool: str
    effect: str
    allowed: bool
    reason: str
    dry_run: bool
    caller: str
    args_digest: Dict[str, Any]
    outcome: str = "pending"
    error: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


# Argument values can contain business data; the audit log records shape and a redacted
# preview rather than raw values, so the trail is useful without becoming a data leak.
_SENSITIVE_HINTS = ("token", "secret", "password", "key", "authorization", "credential")


def _digest_args(args: Dict[str, Any], max_len: int = 80) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (args or {}).items():
        if any(h in k.lower() for h in _SENSITIVE_HINTS):
            out[k] = "<redacted>"
            continue
        try:
            s = v if isinstance(v, (int, float, bool, type(None))) else str(v)
        except Exception:
            s = "<unrepr>"
        if isinstance(s, str) and len(s) > max_len:
            s = s[:max_len] + f"...<+{len(s) - max_len} chars>"
        out[k] = s
    return out


class PolicyEngine:
    """Registry of tool policies + enforcement + audit trail.

    Thread-safe: the MCP server offloads blocking work to worker threads, so rate-limit
    state and the audit buffer are mutated from more than one thread.
    """

    def __init__(self, audit_capacity: int = 1000):
        self._policies: Dict[str, ToolPolicy] = {}
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._audit: Deque[AuditRecord] = deque(maxlen=audit_capacity)
        self._lock = threading.Lock()

    # ── registration ────────────────────────────────────────────────────────
    def register(self, policy: ToolPolicy) -> ToolPolicy:
        with self._lock:
            self._policies[policy.name] = policy
        return policy

    def get(self, tool: str) -> Optional[ToolPolicy]:
        return self._policies.get(tool)

    def all_policies(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in sorted(self._policies.values(), key=lambda p: p.name)]

    # ── global switches (read live so tests/ops can flip without reimport) ──
    @staticmethod
    def writes_enabled() -> bool:
        return _env_true("AGENTKIT_ALLOW_WRITES")

    @staticmethod
    def granted_scopes() -> set:
        raw = os.getenv("AGENTKIT_SCOPES", "").strip()
        if raw == "*":
            return {"*"}
        return {s.strip() for s in raw.split(",") if s.strip()}

    @staticmethod
    def _approval_token() -> str:
        return os.getenv("AGENTKIT_APPROVAL_TOKEN", "").strip()

    # ── enforcement ─────────────────────────────────────────────────────────
    def check(
        self,
        tool: str,
        *,
        args: Optional[Dict[str, Any]] = None,
        caller_scopes: Optional[set] = None,
        approval_token: Optional[str] = None,
        dry_run: bool = False,
    ) -> Decision:
        policy = self._policies.get(tool)
        if policy is None:
            return Decision(False, f"unknown_tool: {tool!r} is not registered")

        if policy.effect != READ and not self.writes_enabled():
            return Decision(
                False,
                f"writes_disabled: {tool!r} has effect={policy.effect}; set "
                "AGENTKIT_ALLOW_WRITES=true to enable mutating tools",
                policy=policy,
            )

        scopes = self.granted_scopes() if caller_scopes is None else caller_scopes
        if policy.scopes and "*" not in scopes:
            missing = [s for s in policy.scopes if s not in scopes]
            if missing:
                return Decision(
                    False,
                    f"missing_scope: {tool!r} requires {sorted(policy.scopes)}; "
                    f"caller is missing {missing}",
                    policy=policy,
                )

        if policy.approval_required and not dry_run:
            required = self._approval_token()
            if not required:
                return Decision(
                    False,
                    f"approval_unavailable: {tool!r} requires approval but "
                    "AGENTKIT_APPROVAL_TOKEN is not configured",
                    policy=policy,
                )
            if (approval_token or "") != required:
                return Decision(
                    False,
                    f"approval_required: {tool!r} is {policy.effect} and needs a valid "
                    "approval_token (a human/supervisor holds it, not the model)",
                    policy=policy,
                )

        if policy.rate_limit:
            now = time.monotonic()
            with self._lock:
                q = self._hits[tool]
                while q and now - q[0] > policy.rate_window:
                    q.popleft()
                if len(q) >= policy.rate_limit:
                    return Decision(
                        False,
                        f"rate_limited: {tool!r} allows {policy.rate_limit} calls per "
                        f"{policy.rate_window}s",
                        policy=policy,
                    )
                q.append(now)

        return Decision(True, "ok", dry_run=dry_run, policy=policy)

    # ── audit ───────────────────────────────────────────────────────────────
    def record(
        self,
        tool: str,
        decision: Decision,
        *,
        args: Optional[Dict[str, Any]] = None,
        caller: str = "unknown",
    ) -> AuditRecord:
        effect = decision.policy.effect if decision.policy else "unknown"
        rec = AuditRecord(
            id=uuid.uuid4().hex[:12],
            ts=datetime.now(timezone.utc).isoformat(),
            tool=tool,
            effect=effect,
            allowed=decision.allowed,
            reason=decision.reason,
            dry_run=decision.dry_run,
            caller=caller,
            args_digest=_digest_args(args or {}),
            outcome="denied" if not decision.allowed else "pending",
        )
        with self._lock:
            self._audit.appendleft(rec)
        if not decision.allowed:
            log.warning("POLICY DENY tool=%s caller=%s reason=%s", tool, caller, decision.reason)
        elif effect != READ:
            log.info("POLICY ALLOW tool=%s effect=%s dry_run=%s caller=%s",
                     tool, effect, decision.dry_run, caller)
        _sink_write(rec)
        return rec

    def complete(self, rec: AuditRecord, *, outcome: str,
                 error: Optional[str] = None, duration_ms: Optional[float] = None) -> None:
        rec.outcome = outcome
        rec.error = error
        rec.duration_ms = duration_ms
        _sink_write(rec, update=True)

    def audit_log(self, limit: int = 100, effect: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._audit)
        if effect:
            items = [r for r in items if r.effect == effect]
        return [r.to_dict() for r in items[:limit]]

    def describe(self) -> Dict[str, Any]:
        return {
            "writes_enabled": self.writes_enabled(),
            "approval_configured": bool(self._approval_token()),
            "granted_scopes": sorted(self.granted_scopes()),
            "tools": self.all_policies(),
            "audit_sink": os.getenv("AGENTKIT_AUDIT_LOG") or None,
        }


def _sink_write(rec: AuditRecord, update: bool = False) -> None:
    """Append the record to AGENTKIT_AUDIT_LOG as JSON Lines, if configured.

    Durable audit is opt-in via env because the default install has nowhere sensible to
    write. Failures here never block a tool call — but they are logged, so a silently
    broken audit sink can't masquerade as "no activity".
    """
    path = os.getenv("AGENTKIT_AUDIT_LOG")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({**rec.to_dict(), "_update": update}) + "\n")
    except Exception as e:  # pragma: no cover - depends on fs perms
        log.warning("audit sink write failed (%s): %s", path, e)


# Process-wide engine. Tools register at import time; the server enforces per call.
policy_engine = PolicyEngine()
