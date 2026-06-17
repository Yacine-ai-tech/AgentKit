# AgentKit — STEPS LOG (living document)

> Continuous engineering log of **every** action on AgentKit from Week 0 to now. Append newest at
> the bottom. Absolute dates. Branch model: feature branch → PR → merge into `develop`. Secrets
> live only in `.env`/`secrets.md` (gitignored) — never here.

## Project in one line
MCP server for business intelligence — 6 tools / 6 resources / 1 prompt over real DataFrame
analytics (insights, forecasting, pg_store), served over SSE on port 8005, with runnable
framework demos (Claude Agent SDK, CrewAI, DSPy) for the "framework-agnostic" positioning.

## Week 0 — scaffold & split (2026-05-20 → 06-05)
- `2cccd3c` initial scaffold from the OmniIntelOS split (mcp_server, workflow, services:
  insights/forecasting/pg_store).
- `76870de` CI pytest; `f13b713` finalize Week 0 (STATUS gitignored); `da6a24f`
  `docker-compose.dev.yml` for the Lightning Studio workflow.

## Phase 3 — real data end-to-end (PR #2)
- **BUG:** the 6 MCP tools returned stubs/lists with wrong kwargs vs the real DataFrame services.
  `acfd650` rewrote them to the DataFrame APIs so all 6 return real data end-to-end.
- `67b0d2e` **fix:** markdown-aware section parser in the reporter (workflow).
- `1f4c509` **fix:** use SSE transport when `MCP_TRANSPORT=sse`.
- **BUG:** insights/forecasting failed import (missing `core.i18n`) → added a `core/i18n.py` shim.
- Merged via **PR #2** (`fix/real-data-end-to-end`, `d053e26`).

## Phase 3 — production-harden demos + MCP protocol test (PR #4)
- `1627c23` runnable demos + MCP-protocol test + Claude Desktop config:
  - **CrewAI demo bugs:** `ValueError: Function must have a docstring` (crewai 1.14) → added
    docstrings; then `GroqException: property 'cache_breakpoint' is unsupported` → switched the
    CrewAI LLM to **Claude Haiku** (`CREWAI_LLM=anthropic/claude-haiku-4-5`). Now produces a real
    executive briefing.
  - **DSPy demo** was a scaffold → made it actually run (`dspy.configure(lm=…)` + pipeline on
    live data).
  - **Claude Agent SDK demo** used non-existent APIs → rewrote to `query` +
    `create_sdk_mcp_server` + `tool`; runs end-to-end with real MCP tool calls (ResultMessage
    success).
  - Added `tests/test_mcp_protocol.py` + `claude_desktop_config.example.json`;
    `requirements.txt` += `claude-agent-sdk`.
- **Validated live** in the Studio: MCP 6 tools / 6 resources / 1 prompt; pytest green; all 3
  framework demos run with real data. Merged via **PR #4** (`feat/prod-harden-demos-mcp`,
  `5f4e0a0`).

## New-account Studio provisioning + .env hardening (2026-06-16)
- Cloned onto `upwork_new` Studio; `.env` recreated with real secrets (Neon Postgres, Anthropic,
  Groq) + `CREWAI_LLM=anthropic/claude-haiku-4-5` + `LLM_LOCAL`; synced local ↔ Studio. (Audit
  had found empty ANTHROPIC/GROQ in the old copy.) No GPU needed (cloud LLM + DataFrame services).

## Current state
Production-validated (`5f4e0a0`): MCP protocol verified, 3 runnable framework demos, real
DataFrame analytics. Deploy/showcase remain (user-gated).

---

## Next — industry & research-standard improvements (planned)
1. **MCP eval harness**: golden transcripts per tool (schema-valid args, deterministic outputs)
   run in CI.
2. **LangGraph agent** variant (per STRATEGY 2.10) alongside the Claude Agent SDK demo.
3. **DSPy compile + telemetry** exported to RAGeval (research-community integration).
4. **Auth + rate-limit** on the SSE endpoint for a hosted demo.
5. **Observability**: structured tool-call traces (OpenTelemetry) for the enterprise audience.

## Phase 3 completion pass (2026-06-16, post-GPU)
- **Audit (user-prompted):** code core done+validated (MCP 6/6/1, LangGraph workflow, CrewAI/
  DSPy/Claude-SDK demos), but Week 9 **writing** was missing.
- **Writing (Week 9):** added `drafts/` (gitignored): `blog_post_3_mcp_agents.md` ("MCP, Not
  Another Agent Framework"), `upwork_proposal_templates.md` (3 niches), `demo_script.md` (60s).

## Comprehensive QA pass (2026-06-16)
- **9 pass/1 skip**. §2.10 verified: Claude Agent SDK, CrewAI, DSPy, LangGraph.
- All 6 projects + both packages green; 28/28 STRATEGY §.10 feature claims code-verified.

## Skip resolved + GPU torch note (2026-06-16)
- The 1 skipped test (`test_mcp_protocol.py`) was skipping because the shared conda env lacked
  `fastmcp` (it IS in requirements.txt `fastmcp>=0.4.0`). Installed fastmcp 3.4.2 → **11 passed,
  0 skipped** (MCP protocol test now runs + validates).

## Remediation — LIVE behavior validation (2026-06-17)
- Added `tests/test_live_workflow.py` (real LLM, skip-if-no-key): **3-agent workflow LIVE**: planner→analyst→reporter on real DataFrame data → substantive report (real LLM, 38s).
- Addresses the "tests prove imports not behavior" gap with a real, measured run.

## FINAL scoreboard + Docker validation (2026-06-17)
- **Docker**: container builds + runs on :8005; added **/health 200** (MCP serves /sse). **Tests 11** + SSE bearer-auth/rate-limit. LangGraph 3-agent workflow validated LIVE (real report). No worldwide agent-tool benchmark maps to custom tools (honest).
- Deployment validated via **Docker** (docker-compose.dev.yml), the isolated per-repo design —
  NOT the shared conda env. All 6 repos: 6/6 containers serve /health.
- **User-gated (cannot be done by the agent):** Railway/Fly deploy, PyPI upload (wheels built),
  Loom recording, sending Upwork proposals, publishing blog/preprint drafts.

## Production-readiness — deploy-today pass (2026-06-17)
- **Cloud $PORT binding + transport:** `mcp_server.py` now picks the port from `MCP_PORT || PORT || 8005`
  and **auto-selects transport**: `MCP_TRANSPORT` if set, else `sse` when a cloud `$PORT` is present,
  else `stdio` locally. So on Railway/Render it serves HTTP/SSE on the platform port out of the box;
  locally it stays stdio (standard MCP). Added `railway.toml` (startCommand forces `MCP_TRANSPORT=sse`,
  healthcheckPath=/health — `/health` is short-circuited 200 by the bearer-auth middleware).
- `.env` gitignored; set `MCP_AUTH_TOKEN` in the platform dashboard to enable bearer auth on SSE.
