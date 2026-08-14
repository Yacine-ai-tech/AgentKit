# Security Policy

## Supported Versions
| Version | Supported |
|---------|-----------|
| latest  | ✅        |

## Reporting a Vulnerability
Report security issues privately via email: contact@ysiddo-ai-projects.app
Do NOT open public GitHub Issues for security vulnerabilities.
Response: 48 hours. Patch: 7 days for critical issues.

---

## Capability Guardrails

AgentKit can expose tools that cause real effects, so enforcement lives in the **tool
server**, not in a prompt. This matters: prompt-level rules are advisory, and the prompt
is exactly what an attacker manipulates. A policy check in the server holds regardless of
what the model was persuaded to attempt, and holds identically across Claude Desktop,
Cursor, LangGraph, CrewAI, the REST facade, or an autonomous loop.

### Typed effects

Every tool declares one:

| Effect | Meaning | Default posture |
|---|---|---|
| `read` | No side effects | Allowed |
| `write` | Creates/modifies state | **Denied** unless writes enabled |
| `destructive` | Irreversible or externally visible | **Denied** unless writes enabled **and** human-approved |

`GET /api/policy` publishes the full envelope — effect, scopes, rate limit, approval
requirement — for every registered tool. Read it (or diff it in CI) to answer "what can
this agent actually do?" without auditing source.

### Enforcement order

1. **Unknown tool** → denied. Nothing runs that wasn't declared.
2. **Writes disabled** → any non-`read` tool denied. `AGENTKIT_ALLOW_WRITES` defaults to
   false, so a default install exposed to the internet cannot mutate anything.
3. **Missing scope** → denied. Tools declare required scopes; callers hold granted ones
   (`AGENTKIT_SCOPES`).
4. **Approval** → `destructive` tools require an `approval_token` matching
   `AGENTKIT_APPROVAL_TOKEN`. **The model never holds this token** — a human or
   supervising system does. The agent proposes; a human authorizes the specific call.
   If approval is required but no token is configured, the call is denied (fails closed).
5. **Rate limit** → per-tool, per-window.
6. **Dry run** → allowed without approval, but the executor simulates instead of
   committing. For SQL, the statement runs inside a transaction that is always rolled
   back, so you get the *real* affected-row count without changing anything.

### Audit

Every invocation is recorded — allowed **and denied** — with the deny reason, effect
class, caller, duration and outcome, at `GET /api/audit`. Denials are the point:
"the agent attempted X and was blocked" is the event an operator needs. Set
`AGENTKIT_AUDIT_LOG=/path/file.jsonl` for a durable JSON Lines trail.

Arguments are recorded as a **redacted digest** — keys matching `token`, `secret`,
`password`, `key`, `credential` are replaced, long values truncated — so the trail is
useful without becoming a data-leak vector.

### Injection posture

- **SQL:** pack parameters are always **bound**, never string-interpolated. A
  model-supplied value cannot alter query structure. Undeclared arguments are rejected
  before reaching the driver, and a `read` tool declaring a `statement:` is refused at
  load time.
- **Prompt injection:** the honest scope. Tools return structured data rather than
  free text that the server then interprets, which narrows the surface — but content
  retrieved from your database *can* still influence a model that reads it. The
  guardrails above are the mitigation that matters: even a fully persuaded model cannot
  exceed the declared capability envelope. Treat effect classes and scopes as the
  security boundary; do not rely on the model refusing.
- **Not provided:** output content filtering, and per-caller identity (scopes are
  process-wide, not per-token). If you need per-tenant authorization, put a gateway in
  front and run one AgentKit per trust boundary.

### Recommended production settings

```bash
AGENTKIT_ALLOW_WRITES=false          # leave off unless you need actions
AGENTKIT_SCOPES=                     # grant explicitly; "*" only for trusted local use
AGENTKIT_APPROVAL_TOKEN=<held by a human, never in the agent's context>
AGENTKIT_AUDIT_LOG=/var/log/agentkit/audit.jsonl
MCP_AUTH_TOKEN=<random>              # bearer auth on the SSE endpoint
REQUIRE_INTERNAL_TOKEN=true          # if a gateway fronts this deployment
```
