# Self-Hosting AgentKit

1. **Install:** `pip install agentkit-mcp` (or run it without installing: `uvx agentkit-mcp`).
2. **Point it at a database:** set `POSTGRES_URL` in the environment or in a `.env` file.
3. **Run:**
   - For an MCP desktop client, the `agentkit-mcp` command serves over stdio. See
     [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) for Claude Desktop, Cursor and Devin
     configuration.
   - For a network deployment, set `PORT` (or `MCP_PORT`) to serve SSE,
     and set `MCP_AUTH_TOKEN` so the endpoint requires a bearer token. For local testing the
     SSE endpoint is `http://localhost:8005/sse`.

## Data source

AgentKit's tools (`query_kpis`, `get_company_health`, `detect_kpi_anomalies`, and so on) read
from whatever Postgres database `POSTGRES_URL` points at; no code change is needed. The hosted
demo uses its own database seeded with sample KPI data covering ten business domains
(`src/agentkit_mcp/data/seed.py`). For your own deployment, seed a database with your data using
the schema in `src/agentkit_mcp/db/schema.sql`. AgentKit does not need any other service of this
project to run.

To expose your own database or HTTP API as tools without writing Python, see
[docs/REUSE.md](docs/REUSE.md).
