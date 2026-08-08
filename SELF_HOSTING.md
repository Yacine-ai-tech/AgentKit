# Self-Hosting AgentKit

1. **Installation:** Run `pip install agentkit-mcp`.
2. **MCP Desktop:** Configure Claude Desktop via `claude_desktop_config.json`.
3. **Running:** `mcp-remote https://agentkit-[YOUR_APP].onrender.com/sse` or locally.

## Data source

AgentKit's tools (`query_kpis`, `get_company_health`, `detect_kpi_anomalies`, etc.) read
from whatever Postgres database `POSTGRES_URL` points at — set via `.env`, no code
changes needed. The live hosted demo happens to point AgentKit at the same instance as
the IntelAI demo, purely to show the two working together on the same real data; that's
a demo-time convenience, not a requirement. For your own deployment, point `POSTGRES_URL`
at a database seeded with your own KPI data using the schema in
`src/agentkit_mcp/db/schema.sql` — AgentKit doesn't need IntelAI running to work.
