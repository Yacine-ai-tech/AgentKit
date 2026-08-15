# Reusing AgentKit From Another Project

AgentKit is a standalone MCP tool server. It does not know what else exists in your
estate, and nothing in this repository names, imports, or hardcodes a sibling project.
Reuse works in both directions, and both directions are generic.

---

## Direction 1 — Another service consumes AgentKit's tools

This is the common case: some other application wants the tools AgentKit exposes.

**Contract (two HTTP calls, no SDK, no coupling):**

```
GET  {AGENTKIT_URL}/api/tools
  -> {"tools": [{"name","description","endpoint","params":[{"name","type","required"}]}],
      "resources": [...], "prompts": [...]}

POST {AGENTKIT_URL}{endpoint}        # body = the tool's params
  -> tool result as JSON
```

Discovery first, then call what you found. The consumer never hardcodes a tool list —
add a tool to AgentKit and every consumer sees it on next discovery.

**Rules for the consuming side (this is what keeps things standalone):**

1. The base URL is **config**, never a literal. Use your own env var —
   `AGENT_TOOLS_URL`, `KPI_TOOLS_URL`, whatever fits your naming.
2. Treat the tool list as **data**. Don't branch on `if tool.name == "query_kpis"`;
   render/expose whatever discovery returns.
3. **Degrade gracefully.** If the URL is unset or the service is unreachable, run
   without those tools. AgentKit being down must never be fatal to your app.
4. Send `X-AgentKit-Internal-Token` (or whatever the deployment requires) only if that
   deployment sets `REQUIRE_INTERNAL_TOKEN=true`.

**Worked example — a voice agent giving its model live business tools.** VoiceFlow's
`services/agent_tools_bridge.py` implements exactly the contract above: it discovers at
connect time, converts each tool's declared params into the function-calling schema its
realtime provider expects, and calls back on tool invocation. Its config is
`AGENT_TOOLS_URL` — pointed at AgentKit in the demo, but any server
speaking the contract works unchanged. Neither side imports the other.

**For StreamPulse / IntelAI / DocIntel**, the same shape applies — add a generic env var
on *their* side (as IntelAI already does for delegated processors via
`DOC_PROCESSOR_URL` / `AUDIO_PROCESSOR_URL`). That is a change in the consuming project,
not here: AgentKit's half of the contract is already generic.

> **Effects matter to consumers.** `GET /api/policy` reports each tool's effect class.
> A consumer that only wants safe reads should filter to `effect == "read"` rather than
> assuming — some tools mutate.

---

## Direction 2 — AgentKit exposes *your* service's data as MCP tools

The reverse: you want your own data available to Claude Desktop / Cursor / any agent,
without writing an MCP server. Describe it in a tool pack — no Python, no fork.

**Over a database:**

```yaml
name: myapp
datasource:
  type: postgres
  url_env: MYAPP_DATABASE_URL      # named env var, never an inline credential
tools:
  - name: recent_orders
    description: Orders placed in the last N days for a customer.
    effect: read
    params:
      - {name: customer_id, type: integer, required: true}
      - {name: days, type: integer, required: false, default: 7}
    query: >
      SELECT id, total, placed_at FROM orders
      WHERE customer_id = %(customer_id)s
        AND placed_at > NOW() - (%(days)s || ' days')::interval
      ORDER BY placed_at DESC
```

**Over an existing HTTP API** (wrap a service you already run — this is how you put an
existing microservice behind MCP without touching it):

```yaml
name: myapi
datasource:
  type: http
  url_env: MYAPI_BASE_URL
tools:
  - name: lookup_customer
    description: Fetch a customer record.
    effect: read
    params:
      - {name: customer_id, type: integer, required: true}
    request:
      method: GET
      path: /customers/{customer_id}
      headers:
        Authorization: $MYAPI_TOKEN     # $NAME reads an env var; never inline a secret
```

Load it with `AGENTKIT_PACKS=/path/to/your/packs`. The tools appear over MCP (stdio and
SSE) *and* at `POST /api/packs/{pack}/{tool}` — same policy enforcement either way.

---

## Direction 3 — Adding your own MCP Resources and Prompts

Tool packs (Direction 2) cover tools. MCP also exposes two other primitive types:

- **Resources** — read-only data anchors at a stable URI (e.g. `myapp://config/current`). An agent or client can pin a resource in its context rather than calling a tool every time.
- **Prompts** — reusable prompt templates a client can invoke by name, optionally with arguments (e.g. `weekly_summary(metric="revenue")`).

The core AgentKit server registers **none of these by default** — intentionally blank. You add your own in a Python extension file:

```python
# my_extension.py
from agentkit_mcp.mcp_server import mcp   # import the shared FastMCP instance

@mcp.resource("myapp://config/current")
async def current_config() -> str:
    """Latest runtime configuration snapshot, pinnable by clients."""
    return '{"mode": "production", "feature_flags": ["new_dashboard"]}'

@mcp.resource("myapp://report/{period}")
async def periodic_report(period: str) -> str:
    """A period-scoped report, e.g. myapp://report/2026-07."""
    return f"Report for {period}: ..."

@mcp.prompt("weekly_summary")
async def weekly_summary_prompt(metric: str = "revenue") -> str:
    """Prompt template for a weekly metric briefing."""
    return (
        f"You are a business analyst. Summarise the {metric} trend for the past week. "
        f"Use the available tools to retrieve the data before writing your summary."
    )
```

Load it by importing it before the server starts — e.g. add a line to your entrypoint, or set `AGENTKIT_EXTENSIONS=my_extension.py` if your deployment supports it. The decorated resources and prompts appear immediately in `resources/list` and `prompts/list` to any connecting MCP client.

> **Design principle.** Domain-specific resources and prompts belong to the consuming project, not the core server. Keeping the server blank means any team can layer their own `@mcp.resource` / `@mcp.prompt` decorators without forking — they get the policy engine and transport for free.

---

## Safety notes for pack authors

- **Parameters are bound, never interpolated.** `%(name)s` goes through the driver's
  parameter binding, so a model-supplied value cannot change query structure. Write the
  query yourself; let the agent fill declared parameters only.
- **Declare effects honestly.** `read` / `write` / `destructive` drive real enforcement
  (see [SECURITY.md](../SECURITY.md#capability-guardrails)). A `read` tool may not use
  `statement:` — loading rejects it.
- **Undeclared arguments are refused** before reaching SQL.
- **Writes are off until enabled.** `AGENTKIT_ALLOW_WRITES=true` plus any scopes you
  declare; `destructive` additionally needs a human-held approval token.
- **Every call is audited** — allowed and denied — at `GET /api/audit`.
