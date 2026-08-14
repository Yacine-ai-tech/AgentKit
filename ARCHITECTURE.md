# AgentKit — Architecture & Audit Notes

Single source of truth for what's actually verified vs. what's still assumed. Written
across three passes (2026-08-10/11). Update this file, don't let it drift — that's the
whole point of it existing.

## Pass 3 (2026-08-11) — scope change: from BI wrapper to governed tool server

The first two passes fixed bugs but left the positioning problem intact: the six tools
were hardcoded to one project's `kpi_metrics` schema and everything was read-only, so
"AgentKit" was really *an MCP wrapper around one database*. Pass 3 changed the product,
not just the defects. See STRATEGY.md §2.11 for the reframe.

**Built and verified live:**

- `core/llm_router.py` — the STRATEGY.md §2.10 tier router (default/reasoning/judge/
  local), now actually wired into `workflow.py`. Closes the `INFERENCE_MODE`/`LLM_LOCAL`
  gap that pass 2 could only document. Self-hosted inference is fully env-driven
  (`LOCAL_LLM_ENDPOINT`/`OLLAMA_HOST` + `LOCAL_LLM_TOKEN`) and points at *any* endpoint
  you control — localhost, your own GPU box, or a shared inference host. **Verified** by
  intercepting the real HTTP layer: `INFERENCE_MODE=local` resolves every tier to the
  local model, requests go to `{base}/api/chat` for `ollama_chat/*` and
  `{base}/api/generate` for `ollama/*`, and the bearer token *is* transmitted (needed
  for an auth-requiring shared host). No local model was run — this machine has ~1GB RAM
  free and no GPU — so what is verified is the **routing and auth**, not inference
  quality on a local model.
- `core/policy.py` — typed effects (`read`/`write`/`destructive`) + enforcement:
  fail-closed write switch, scopes, human-held approval token, per-tool rate limits,
  dry-run, and an audit trail that records denials with reasons and redacts sensitive
  args. 14 tests, all asserting **denials**.
- `toolpacks.py` + `pack_runtime.py` + `packs/annotations.yaml` — declarative YAML tools
  over Postgres or HTTP, registered as real MCP tools with real JSON Schemas synthesized
  from declared params. Params are bound, never interpolated; undeclared args refused;
  a `read` tool declaring `statement:` is rejected at load.
- New endpoints: `/api/policy`, `/api/audit`, `/api/packs`, `/api/llm-routing`,
  `POST /api/packs/{pack}/{tool}`.
- `docs/REUSE.md` — the generic both-directions reuse contract.

**Live end-to-end action-path verification** (real Neon DB — AgentKit's own database,
confirmed with the user; `kpi_annotations` created via `scripts/init_annotations.sql`):

| Step | Result |
|---|---|
| write with writes **disabled** | `403 writes_disabled` ✓ |
| destructive with writes disabled | `403 writes_disabled` ✓ |
| dry-run write | `would_affect_rows:1, committed:false` ✓ (real count, rolled back) |
| real write | `affected_rows:1, committed:true` ✓ |
| read-back | row returned ✓ |
| destructive, **no** approval token | `403 approval_required` ✓ |
| destructive, **wrong** token | `403 approval_required` ✓ |
| destructive dry-run (no token) | permitted, not committed ✓ |
| destructive, **correct** human token | committed, `retracted_at` set ✓ |
| audit trail | all of the above recorded, allows and denies ✓ |

Test rows were tagged `author='agentkit-verify'` and deleted afterwards; `SELECT count(*)`
confirmed **0 rows remain**. The (empty) table itself was kept — it's the pack's schema.

**Bugs found and fixed in pass 3:**

1. **The CrewAI/DSPy demos could not run at all.** Both imported `from core.logger` and
   `from mcp_server` — the pre-package-refactor flat layout. `python demos/crewai_demo.py`
   died with `ModuleNotFoundError` on the first line. Pass 2 marked these "verified by
   reading the code", which is exactly the failure mode reading cannot catch. Fixed to
   proper package imports and **both now run live** (CrewAI: real 3-agent crew, real
   tool calls, real Anthropic usage, real briefing citing real KPI values; DSPy: real
   bootstrap compilation, `eval_score=0.6`).
2. **DSPy demo produced empty output** even when it ran — `max_tokens=1024` was consumed
   by ChainOfThought's reasoning field before it emitted the answer. Now 4096, override
   via `DSPY_MAX_TOKENS`; plan and report populate correctly.
3. **My own regression, caught by tests:** an `else:` branch I added swallowed the six
   `@mcp.resource` decorators, so `resources/list` returned **0**. Fixed; the protocol
   test that caught it is why it didn't ship.
4. **Pack SQL bug:** a parameter appearing only in an `IS NULL` test gives Postgres
   nothing to infer a type from (`could not determine data type of parameter $1`). Fixed
   with explicit `::text`/`::boolean` casts, noted in the pack so it isn't "cleaned up".

**Corrected overclaims (docs, not code):**

- `RESEARCH.md` previously presented MCP's own JSON-Schema parameter validation as a
  formal contribution with a "validation function". That is standard MCP behaviour, not
  novelty. Replaced with the defensible claim — typed effects enforced at the protocol
  boundary, with a refusal benchmark — and an explicit limitations section.
- The same file quoted "> 90% tool selection accuracy" and "> 85% report quality".
  Those rates imply a sample size that does not exist (the eval is N=4). Replaced with
  actual counts and a note that publication needs a much larger adversarial set.

**Still not done / not verified:**

- The Claude Agent SDK demo is still **read-verified only** — `claude-agent-sdk` also
  needs the `claude` CLI as a runtime, which isn't installed here. CrewAI and DSPy are
  now genuinely executed; this one is not.
- Scopes are process-wide, not per-caller identity. Multi-tenant needs a gateway per
  trust boundary (documented in SECURITY.md rather than pretended away).
- No output content filtering, no prompt-injection *detection* (the guardrails bound
  what an injection can cause, which is the defensible property — not the same thing).
- `/api/summary` latency issue from pass 2 is unchanged (see below).

## System shape (as it actually runs, not as marketed)

```
Claude Desktop / Cursor / LangGraph / VoiceFlow (generic agent-tools contract)
                              │ MCP (SSE) or REST (GET /api/*)
                    mcp_server.py (root shim, sys.path→src, imports agentkit_mcp.mcp_server)
                              │
        ┌─────────────────────┴─────────────────────┐
        │ FastMCP: 6 tools, 6 kpi:// resources,      │  agentkit_mcp/web_app.py
        │ 1 prompt (mcp_server.py)                   │  FastAPI facade: /api/* delegates
        │ bearer-auth + rate-limit (auth_middleware)  │  to the SAME tool functions, plus
        └─────────────────────┬─────────────────────┘  a separate in-memory admin.py demo
                              │ (async, offloaded to worker thread — see fix #2 below)
                    services/pg_store.py → Neon Postgres (kpi_metrics)
                    services/insights.py / forecasting.py → pandas/sklearn, CPU-only
                              │
                    workflow.py — LangGraph 3-agent (planner/analyst/reporter) via LiteLLM
```

One real data layer, one set of tool functions. The MCP tools, the REST facade, the
LangGraph workflow, the Claude Agent SDK demo, and the CrewAI demo all call the exact
same six functions in `mcp_server.py` — verified by reading every call site, not just
the docstrings claiming it.

## Confirmed working (live-tested against the real Neon DB + real provider keys)

- `python mcp_server.py` boots, serves SSE (bearer-gated) + REST facade on one port.
- `/health`, `/api/tools`, `/api/kpis`, `/api/health-score`, `/api/metrics`,
  `/api/anomalies`, `/api/forecast` — all hit real Postgres, real pandas/sklearn compute,
  real (non-fabricated) numbers. Verified with curl against real data.
- `MCP_TRANSPORT=stdio` (the mode Claude Desktop/Cursor/Devin actually use) — real
  JSON-RPC 2.0 `initialize` handshake, `tools/list`, and a real `tools/call` returning
  live database data, all verified over an actual subprocess stdin/stdout pipe. See bug
  #10 below — this didn't work at all before this session's second pass.
- Full pytest suite: **27/27 passing** (was 24/25 + 1 pre-existing-fragile at session
  start; +2 new tests added — `tests/test_stdio_transport.py` — to guard the stdio fix).
- Frontend production build (`npm run build`) succeeds clean; the built SPA + REST API
  served together from one process (the real `Dockerfile CMD`, single origin, no dev
  proxy) — same-origin `/`, `/assets/*`, `/api/*` all verified working together.
- `flake8 src/ --max-line-length=100 --ignore=E501` (the exact CI check): clean, 0
  findings.
- **Cross-project integration, live-tested at two levels, not just read**:
  1. Module-level: ran VoiceFlow's real, unmodified `services/agent_tools_bridge.py`
     against a local AgentKit — `discover_tools()` found all 6 real tools,
     `call_tool("get_company_health", {})` returned real data from the live DB, and
     `openai_tools()` produced a correct OpenAI Realtime API function-calling schema.
  2. Endpoint-level (stronger proof — confirms the bridge is actually wired in, not
     orphaned): launched VoiceFlow's real FastAPI app with `AGENT_TOOLS_URL` set, opened
     a real WebSocket to its actual `@app.websocket("/realtime")` voice-agent endpoint
     (`api.py:611`), and watched VoiceFlow's own server log fire
     `agent-tools discovery: found 6 tool(s) at http://localhost:8005` automatically on
     connect, immediately followed by a successful real Gemini Multimodal Live session
     handshake (`{"type":"ready","message":"Connected to Gemini Multimodal Live..."}`).
     `agent_tools_bridge` is called from both provider branches (OpenAI and Gemini) at
     both the tool-declaration stage (`api.py:657,801`) and the tool-execution stage
     (`api.py:753,842`) — genuinely load-bearing, not dead code.
  Nothing on either side hardcodes the other project's name/URL/schema — see
  "Connecting other projects" below for what this means for StreamPulse/IntelAI/any
  other voice platform.
- `.env`/`.env.example` across all 6 sibling projects: no line-ending corruption, no
  leaked secrets, no cross-project URL leaks in any `.env.example`.
- 2026 stack upgrade (STRATEGY.md §2.10): MCP resources+prompts and the LangGraph
  workflow verified **live** (real HTTP calls, real data). The Claude Agent SDK demo and
  DSPy research scaffold are verified **by reading the code** (they correctly wrap the
  same 6 real tool functions) but not executed — `claude-agent-sdk` isn't installed in
  this environment. The CrewAI demo is verified by reading the code only — `crewai` isn't
  installed here either. Don't take "present and correctly wired" as "executed
  end-to-end" for those two; if you need that guarantee, run
  `demos/claude_agent_sdk_demo.py` and `demos/crewai_demo.py` yourself after
  `pip install claude-agent-sdk crewai`.

## Bugs found live and fixed this session

1. **`.env` was never actually loaded locally** (`src/agentkit_mcp/core/config.py`).
   `load_dotenv()` pointed at `src/agentkit_mcp/.env`, which doesn't exist — two
   directory levels short of the real repo-root `.env`. Silent failure (dotenv doesn't
   error on a missing path), so every local run fell back to whatever was already in the
   shell's environment. Reproduced live: following the README's own Quick Start
   (`cp .env.example .env && python mcp_server.py`) crashed on startup because the real
   `.env` was never read. **Fixed**: path now resolves to the actual repo root
   (`parents[3]`), verified via a fresh-clone boot test with the corrected
   `.env.example` — boots clean, fails gracefully (not silently, not fabricated) when
   Postgres is unreachable.
2. **Event loop blocked by synchronous DB calls** (`mcp_server.py`). `query_kpis`,
   `get_company_health`, `detect_kpi_anomalies`, `forecast_metric`, and
   `list_available_metrics` are `async def` but called `pg_store.get_kpi_metrics(...)` —
   a plain synchronous psycopg call — directly, with no thread offload. Under any
   concurrent load this froze the *entire* server (SSE, health checks, everything) on
   the single asyncio event loop. Reproduced live: 4 sequential `/api/summary` calls hung
   the whole process for 2+ minutes. **Fixed**: added `_run_db()` (wraps
   `anyio.to_thread.run_sync`) and routed every pg_store call site through it. Verified:
   `/health` now responds in ~5ms while 8 concurrent `/api/summary` calls are in flight —
   the event loop is provably no longer blocked.
3. **Connection pool didn't recover from dead connections** (`services/pg_store.py`).
   Neon closes idle/over-limit connections server-side without telling the pool; without
   a liveness check on checkout, the pool kept handing out dead connections and every
   subsequent call failed with "server closed the connection unexpectedly" — this
   actually happened live during my own stress-testing (see caveat below) and didn't
   self-heal. **Fixed**: added `check=ConnectionPool.check_connection` to the pool
   config.
4. **`MCP_AUTH_TOKEN` required but undocumented everywhere a user would hit it first** —
   `.env.example` didn't list it (server hard-crashes without it — confirmed live), and
   the README's Claude Desktop JSON config example didn't include it either (same crash
   via that path). **Fixed**: rewrote `.env.example` to include it plus every other var
   `config.py` actually reads (`LLM_DEFAULT`/`LLM_REASONING`/`LLM_JUDGE`/`LLM_LOCAL`,
   `INFERENCE_MODE`, `GROQ_API_KEY`, `MCP_TRANSPORT`/`MCP_PORT`,
   `REQUIRE_INTERNAL_TOKEN`); updated the README's Claude Desktop example and replaced
   the "LLM_ENDPOINT/LLM_TOKEN route via LiteLLM" claim (those two vars are dead —
   defined in `config.py`, never consumed by any LLM call) with the real routing
   mechanism (`LLM_DEFAULT`/`LLM_REASONING` per-agent in `workflow.py`).
5. **Dead/broken entrypoint files**. `scripts/mcp_server.py` and `scripts/web_app.py`
   were byte-identical unreferenced duplicates of the root files — deleted. Root
   `web_app.py` (and its now-deleted `scripts/` twin) did `from agentkit_mcp.web_app
   import app`, but `agentkit_mcp/web_app.py` only exports `build_app()`, no module-level
   `app` — confirmed live `ImportError` on every invocation. **Fixed**: `app =
   build_app()`.
6. **Root `mcp_server.py`'s "WARM UP ML MODELS" block was dead weight** — it ran *after*
   `_serve_sse()` (which blocks until shutdown), did nothing, and unconditionally logged
   "pre-warmed successfully". Removed.
7. **Plaintext passwords leaked via `GET /api/users`** (`src/api/admin.py` — the
   documented in-memory demo admin layer, publicly reachable since
   `REQUIRE_INTERNAL_TOKEN=false` in production, consistent with every other project in
   the portfolio's own default). Passwords were stored and returned as-is. **Fixed**:
   strip `password` from the response.
8. **Stale doc**: README claimed PyPI `v0.1.4`; `pyproject.toml` (and the actual
   published package) is `v0.1.8`. Fixed.
9. **Flaky test unmasked by fix #1**: `test_rate_limit_429` passed `token=None` intending
   "auth disabled for this test", but the middleware treats `None` as "fall back to
   `os.getenv("MCP_AUTH_TOKEN")`" — so once fix #1 made `.env` loading actually work, any
   test-session import of `agentkit_mcp.core.config` leaked the real token into the
   process env and made this test flaky (401 instead of 429). This was always fragile;
   fix #1 just exposed it. **Fixed**: test now passes `token=""` (explicitly falsy,
   bypasses the env fallback), verified stable with and without an ambient
   `MCP_AUTH_TOKEN`.
10. **`MCP_TRANSPORT=stdio` was a phantom feature — the single biggest finding of the
    second audit pass.** All three shipped IDE configs
    (`claude_desktop_config.example.json`, `cursor_mcp.example.json`,
    `devin_mcp.example.json`), `docs/INTEGRATION_GUIDE.md`, and even
    `tests/test_mcp_client.py`'s docstring ("Simulates ... JSON-RPC 2.0 stdio protocol
    calls") all described/relied on a local stdio integration path. `grep -rn
    MCP_TRANSPORT` across every `.py` file returned **zero hits** — nothing ever read
    that env var. `mcp_server.py`'s `__main__` unconditionally set `transport = "sse"`
    and started an HTTP/uvicorn server regardless. Any client spawning the process
    expecting stdio JSON-RPC framing (which is exactly what all three shipped configs
    do) would get log lines and an open HTTP port instead of a protocol handshake —
    silent, total failure to connect, for literally the primary documented onboarding
    path. **Fixed properly, not just documented**: added a real `MCP_TRANSPORT=stdio`
    branch calling `mcp.run(transport="stdio", show_banner=False)` in both entrypoints
    (root `mcp_server.py` and `agentkit_mcp/mcp_server.py`'s `__main__`), *and* fixed
    `core/logger.py` to log to stderr instead of stdout (stdout must carry nothing but
    JSON-RPC frames in this mode — logging to stdout would have silently corrupted the
    protocol stream even with the transport switch in place). Verified with a real
    subprocess: `initialize` handshake, `tools/list`, and a real `tools/call` all
    round-tripped correctly with clean stdout/stderr separation — see
    `tests/test_stdio_transport.py`, now a permanent regression test.

## Removed as dead/orphaned (not fixed, deleted)

`frontend/src/pages/AdminPage.jsx` and `frontend/src/api.js` — not routed in `App.tsx`,
not in the nav, and imported `../context/AuthContext` and `../components/ui`, neither of
which exist anywhere in this repo (leftover from a different sibling project's
auth-scaffold pattern). The backend admin API they were meant to drive is real and
correctly documented in `ApiDocs.tsx`/`UserGuidePage.tsx` as an in-memory demo layer —
only the promised "dashboard" UI was fake. Updated the one doc line that referenced it.
Frontend production build verified clean after removal.

## Connecting other projects (respecting the standalone requirement)

AgentKit exposes exactly one generic, undocumented-to-any-specific-consumer contract for
this: `GET /api/tools` → `{"tools":[{"name","description","endpoint","params"}]}`, then
`GET {endpoint}?<params>` → JSON. That's it. It's the same shape `web_app.py`'s own
`TOOL_META` produces and the same shape VoiceFlow's `agent_tools_bridge.py` consumes —
verified live above. AgentKit does not know VoiceFlow exists; nothing in this repo names
it. Any client — a different voice platform, StreamPulse, IntelAI, a cron job — can
consume AgentKit the same way, by:
1. `GET {AGENTKIT_URL}/api/tools` to discover what's callable.
2. `GET {AGENTKIT_URL}{endpoint}?params` to call it, adding
   `X-OmniIntel-Internal-Token: <shared secret>` if `REQUIRE_INTERNAL_TOKEN=true` on that
   deployment.

For StreamPulse or IntelAI to consume AgentKit specifically, the correct pattern
(matching how IntelAI already does this for DocIntel/VoiceFlow via
`DOC_PROCESSOR_URL`/`AUDIO_PROCESSOR_URL`, and StreamPulse via `DOCINTEL_URL`) is a new,
equally generic env var on *their* side — e.g. `AGENT_TOOLS_URL` (StreamPulse and IntelAI
don't currently have one; VoiceFlow's is the only existing instance of this pattern) —
never a hardcoded AgentKit URL/schema in their code. That's a change on the consuming
project's side, not AgentKit's; AgentKit's half of the contract (the discovery response
shape) is already generic and already correct for this.

## Known limitations — documented, not fixed this session

- **`INFERENCE_MODE`/`LLM_LOCAL` declared but not wired.** `config.py` defines both (and
  a test checks they exist), matching the portfolio-wide "never assume a cloud provider
  is the only option" constraint in spirit, but `workflow.py`'s planner/reporter always
  call `settings.LLM_REASONING` directly — there's no actual fallback path to
  `LLM_LOCAL`/Ollama when `INFERENCE_MODE=local`. Every sibling project (DocIntel Route
  B, VoiceFlow's local/remote ASR) implements this real toggle; AgentKit only declares
  it. Didn't implement this session because it touches live LLM call behavior I can't
  fully verify without a local Ollama install.
- **`get_executive_summary` / `/api/summary` is slow** (3 sequential unfiltered-ish DB
  round trips — `get_company_health()`, `query_kpis(limit=10)` with no domain filter, and
  `detect_kpi_anomalies(domain="Finance")` — each taking ~6–7s because `query_kpis`
  fetches the *entire* table into pandas before applying `limit` in Python instead of
  pushing `LIMIT`/domain filtering down to SQL). Not a hang (that was bug #2, now fixed),
  but a real ~15–20s worst-case latency on the README's own demo script's "Generate a
  full executive report" step. Worth a follow-up: push filtering to SQL in
  `pg_store.get_kpi_metrics`.
- **90-second embedded Loom demo** (STRATEGY.md §2.4 checklist) — not present in the
  README as an embedded video; only a live-site link. Not code-verifiable either way.

## Caveat on how bug #3 was found

Bug #3 (dead connection pool) was surfaced by my own concurrent stress-testing
(8 concurrent `/api/summary` calls) against the **live production Neon database**
(`.env` holds real prod credentials — there's no separate local/staging DB). Confirmed
the live Render deployment (separate process, separate pool) was unaffected throughout;
only my local test process's pool went stale, and it fully recovered after the
`check_connection` fix. No data was written or corrupted (every endpoint touched was
read-only). Flagging this so it isn't mistaken for an incident — it wasn't one, but it's
why the fix exists.

## Pass 4 (2026-08-14) — UI parity & Hygiene Pass
- **UI ↔ Backend Parity Gap Closed:** The `frontend` React app was completely unaware of the new policy capabilities (effects, scopes, writes_enabled) added in Pass 3.
  - Fixed `lib/api.ts` to include `PolicyResponse`, `ToolPolicy`, and the `api.policy()` fetcher.
  - Rewrote `pages/Tools.tsx` to query `/api/policy` and map its output onto the tool cards. It now correctly displays global capability switches (Writes ENABLED/DISABLED, Approval CONFIGURED/NOT SET) at the top of the page.
  - Tool cards now display `effect` tags (`[READ]`, `[WRITE]`, `[DESTRUCTIVE]`) and list required `scopes`.
  - Added checkboxes for `dry_run` and an input field for `approval_token` if a tool is `write` or `destructive`.
- **Hygiene & Secrets Pass:** 
  - Verified that `.env.example` has no leaked production URLs or hardcoded third-party tokens. All database URLs default to a placeholder `postgresql://user:password@localhost/dbname`.
  - Removed stray and corrupted `.env` backup files (`.env.bak-20260811`, `.env.bak-corrupted`) left over from the workspace splitting.
  - Verified no stray "TODO" or internal hack comments remained in `src/`.
