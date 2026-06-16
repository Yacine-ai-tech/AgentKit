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
