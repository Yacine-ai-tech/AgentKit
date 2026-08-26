import React from 'react';
import { BookOpen, Monitor, Terminal, FileCode, CheckCircle, ShieldAlert,
         Brain, Globe, Wrench, Database, MessageSquareQuote, GitBranch,
         Activity, BarChart3, Cable } from 'lucide-react';

// Same resolution order as lib/api.ts / ApiDocs.tsx: an explicit VITE_API_BASE_URL wins
// (split deployments), otherwise fall back to the current origin — so the sample MCP
// client config below always shows wherever this guide is actually being served from,
// not a hardcoded domain.
const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" ? window.location.origin : "");

export default function UserGuidePage() {
  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-8">
        <BookOpen className="w-10 h-10 text-blue-500" />
        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
          AgentKit — Complete User Guide
        </h1>
      </div>

      <p className="text-lg text-gray-300 mb-8 leading-relaxed">
        AgentKit is a <strong className="text-blue-400">policy-governed Model Context Protocol (MCP) server for AI agents</strong>.
        It enables declarative, YAML-defined tool packs over any Postgres or HTTP datasource and ships with a bundled
        reference BI pack for company KPIs, health scoring, anomaly detection, forecasting, and executive snapshots.
        It is framework-agnostic: the same tools work seamlessly from Claude Desktop, Cursor, LangGraph, the Claude Agent SDK,
        and CrewAI with strict parameter binding and dry-run policy safety.
      </p>

      <div className="space-y-8 text-gray-200">

        {/* What is AgentKit */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Brain className="w-6 h-6 text-purple-400" /> What is AgentKit?
          </h2>
          <div className="space-y-4">
            <p className="text-gray-300">
              Under the hood, AgentKit is a modular Python MCP platform (<code className="bg-gray-900 px-1 rounded">agentkit_mcp/mcp_server.py</code> and <code className="bg-gray-900 px-1 rounded">agentkit_mcp/toolpacks.py</code>)
              that exposes capabilities two ways:
            </p>
            <ul className="list-disc list-inside text-sm text-gray-300 space-y-2 ml-2">
              <li><strong className="text-blue-400">As an MCP server</strong> — tool packs, resources and prompts reachable from any MCP client over stdio (local) or SSE (hosted), gated by a fine-grained policy engine.</li>
              <li><strong className="text-green-400">As a REST facade</strong> (<code className="bg-gray-900 px-1 rounded">agentkit_mcp/web_app.py</code>) — every <code className="bg-gray-900 px-1 rounded">/api/*</code> route delegates to the exact same tool functions, which is how this dashboard renders live telemetry and capability inspection in your browser. See the <strong>API Docs</strong> page for every endpoint.</li>
            </ul>
            <p className="text-gray-300">
              A business user asking an agent "what's our finance health look like, and is anything off?" gets answered
              by tools chaining together — <code className="bg-gray-900 px-1 rounded">get_company_health</code>,
              then <code className="bg-gray-900 px-1 rounded">detect_kpi_anomalies</code> — with bound parameters and without the agent ever
              seeing raw credentials.
            </p>
          </div>
        </section>

        {/* Declarative Packs & Reference BI Tools */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Wrench className="w-6 h-6 text-green-400" /> Reference BI Pack & Declarative Tool Packs
          </h2>
          <p className="text-gray-300 mb-4 text-sm">
            AgentKit is fully extensible: load custom YAML packs from <code className="bg-gray-900 px-1 rounded">AGENTKIT_PACKS</code> to connect any table or API. The bundled Reference BI Pack provides 6 out-of-the-box analytical tools:
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            <ToolCard color="green" name="query_kpis" title="Look up KPIs" ask="“What were our Growth metrics last quarter?”" />
            <ToolCard color="blue" name="get_company_health" title="Company health score" ask="“How healthy is the business right now?”" />
            <ToolCard color="red" name="detect_kpi_anomalies" title="Find outliers" ask="“Is anything unusual in our Finance numbers?”" />
            <ToolCard color="purple" name="forecast_metric" title="Forecast a metric" ask="“Where is revenue headed over the next 6 months?”" />
            <ToolCard color="yellow" name="list_available_metrics" title="Discover what's tracked" ask="“What metrics and domains do we even have data for?”" />
            <ToolCard color="cyan" name="get_executive_summary" title="One-shot executive snapshot" ask="“Give me the state of the business in one summary.”" />
          </div>
          <p className="text-xs text-gray-400 mt-4">
            All analytical tools read from the live <code className="bg-gray-900 px-1 rounded">kpi_metrics</code> table via
            <code className="bg-gray-900 px-1 rounded ml-1">POSTGRES_URL</code>. If that connection isn't configured,
            tools return an explicit error — never fabricated numbers. Full parameter lists and JSON response
            shapes are on the <strong>API Docs</strong> page.
          </p>
        </section>

        {/* Resources & prompt */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Database className="w-6 h-6 text-cyan-400" /> Resources & the Briefing Prompt
          </h2>
          <p className="text-gray-300 mb-3 text-sm">
            Beyond tools, MCP has two other first-class primitives, and AgentKit registers one of each kind that matters:
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-cyan-400 text-lg mb-2">6 Resources</h3>
              <p className="text-sm text-gray-300 mb-2">
                <code className="bg-gray-950 px-1 rounded">kpi://Finance/latest</code>, and the same for
                Growth, Operations, People, ESG and IT_Ops — each is a standing, addressable read that
                resolves to the latest 10 KPI rows for that domain. Agents can pull these directly without
                deciding on tool parameters first.
              </p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-green-400 text-lg mb-2 flex items-center gap-2"><MessageSquareQuote className="w-4 h-4" /> 1 Prompt</h3>
              <p className="text-sm text-gray-300">
                <code className="bg-gray-950 px-1 rounded">monthly_executive_briefing(month)</code> hands the
                agent a structured instruction template — KEY FINDING, EVIDENCE, ROOT CAUSE, RECOMMENDED ACTION,
                RISK IF UNADDRESSED — so briefings come back in a consistent, decision-ready shape instead of
                free-form prose.
              </p>
            </div>
          </div>
        </section>

        {/* Connecting */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Cable className="w-6 h-6 text-orange-400" /> Connecting an Agent
          </h2>
          <p className="text-gray-300 mb-4 text-sm">
            The <strong>Connect</strong> page in this dashboard has copy-paste-ready configs and stays in sync with
            the repo's example files. There are two real ways in:
          </p>

          <div className="space-y-6">
            <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-lg text-gray-100 flex items-center gap-2 mb-3">
                <FileCode className="w-5 h-5 text-orange-400" /> Remote — hosted SSE (no local setup)
              </h3>
              <p className="text-sm text-gray-300 mb-3">
                Point Claude Desktop at the hosted server via <code className="bg-gray-950 px-1 rounded">mcp-remote</code>,
                using a bearer token (<code className="bg-gray-950 px-1 rounded">MCP_AUTH_TOKEN</code>):
              </p>
              <pre className="bg-gray-950 p-4 rounded-lg text-sm font-mono text-green-300 overflow-x-auto">
{`{
  "mcpServers": {
    "agentkit-remote": {
      "command": "npx",
      "args": ["-y", "mcp-remote",
               "${BASE_URL}/sse",
               "--header", "Authorization: Bearer \${MCP_AUTH_TOKEN}"],
      "env": { "MCP_AUTH_TOKEN": "<your token>" }
    }
  }
}`}
              </pre>
            </div>

            <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-lg text-gray-100 flex items-center gap-2 mb-3">
                <Terminal className="w-5 h-5 text-gray-400" /> Local — stdio (your own database)
              </h3>
              <p className="text-sm text-gray-300 mb-3">
                Run the server on your machine against your own PostgreSQL instance. This is also the pattern
                used by the <code className="bg-gray-950 px-1 rounded">claude_desktop_config.example.json</code>,
                <code className="bg-gray-950 px-1 rounded ml-1">cursor_mcp.example.json</code> and
                <code className="bg-gray-950 px-1 rounded ml-1">devin_mcp.example.json</code> files shipped in the repo root:
              </p>
              <pre className="bg-gray-950 p-4 rounded-lg text-sm font-mono text-green-300 overflow-x-auto">
{`{
  "mcpServers": {
    "agentkit": {
      "command": "python",
      "args": ["-m", "agentkit_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/AgentKit/src",
        "POSTGRES_URL": "postgresql://user:password@localhost/neondb?sslmode=require"
      }
    }
  }
}`}
              </pre>
              <p className="text-xs text-gray-400 mt-3">
                Without <code className="bg-gray-900 px-1 rounded">POSTGRES_URL</code> pointed at a database seeded
                with the <code className="bg-gray-900 px-1 rounded">kpi_metrics</code> table, tools return an
                explicit "data layer unavailable" error rather than silently faking data.
              </p>
            </div>
          </div>
        </section>

        {/* Beyond single tool calls: workflow + demos */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <GitBranch className="w-6 h-6 text-amber-400" /> The Agent Workflow
          </h2>
          <p className="text-gray-300 mb-3 text-sm">
            The <strong>Workflow</strong> page runs a real 3-agent LangGraph pipeline
            (<code className="bg-gray-900 px-1 rounded">agentkit_mcp/workflow.py</code>) end to end against live data:
          </p>
          <div className="grid md:grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-blue-400 mb-1">1. Planner</h3>
              <p className="text-sm text-gray-300">Breaks your question into a 3-4 step analysis plan.</p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-purple-400 mb-1">2. Analyst</h3>
              <p className="text-sm text-gray-300">Routes on keywords in the question and calls the same MCP tools against live PostgreSQL.</p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-amber-400 mb-1">3. Reporter</h3>
              <p className="text-sm text-gray-300">Synthesizes the evidence into a KEY FINDING / EVIDENCE / ROOT CAUSE / RECOMMENDED ACTION / RISK report, exportable as Markdown.</p>
            </div>
          </div>
          <p className="text-gray-300 text-sm mb-2">
            You can also trigger it directly: <code className="bg-gray-900 px-1 rounded">POST /api/workflow/run</code> with
            <code className="bg-gray-900 px-1 rounded ml-1">{`{"question": "..."}`}</code> — this spends LLM credits and
            takes a few seconds since it's a live 3-step chain, not a cached response.
          </p>
          <p className="text-gray-300 text-sm">
            Three integration demos ship in the repo showing the same tools wired into other frameworks — all calling
            the identical functions in <code className="bg-gray-900 px-1 rounded">mcp_server.py</code>:
          </p>
          <ul className="list-disc list-inside text-sm text-gray-300 space-y-1 ml-2 mt-2">
            <li><code className="bg-gray-900 px-1 rounded">demos/claude_agent_sdk_demo.py</code> — the tools exposed as an in-process Claude Agent SDK MCP server.</li>
            <li><code className="bg-gray-900 px-1 rounded">demos/crewai_demo.py</code> — the same tools wrapped as CrewAI <code className="bg-gray-950 px-0.5 rounded">@tool</code> functions in a Researcher → Analyst → Reporter crew.</li>
            <li><code className="bg-gray-900 px-1 rounded">research/dspy_experiment.py</code> — a DSPy research scaffold treating planner → analyst → reporter as an optimizable program (not production; see its own docstring).</li>
          </ul>
        </section>

        {/* Dashboard pages */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Monitor className="w-6 h-6 text-blue-400" /> What's in This Dashboard
          </h2>
          <p className="text-gray-300 mb-4 text-sm">
            The dashboard is a thin client over the REST facade — every page below reads live data through the same
            functions the MCP tools use, so what you see here is exactly what a connected agent would get.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-gray-100 flex items-center gap-2 mb-1"><BarChart3 className="w-4 h-4 text-purple-400" /> Business Intelligence & Tools</h3>
              <p className="text-sm text-gray-300">Run any of the 6 tools live from a form and see the exact JSON an agent would receive.</p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-gray-100 flex items-center gap-2 mb-1"><Activity className="w-4 h-4 text-green-400" /> Observability</h3>
              <p className="text-sm text-gray-300">Real request telemetry — every call into <code className="bg-gray-950 px-1 rounded">/api/*</code> traced with method, path, status and latency, from an in-memory ring buffer polled every 2.5s. Not simulated.</p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-gray-100 flex items-center gap-2 mb-1"><GitBranch className="w-4 h-4 text-amber-400" /> Evaluation Benchmark</h3>
              <p className="text-sm text-gray-300">
                A reproducible LLM-as-judge benchmark (<code className="bg-gray-950 px-1 rounded">python eval/run_agent_eval.py</code>)
                scoring the LangGraph agent's tool-selection accuracy and answer groundedness on 4 core
                multi-tool queries — current published result is 100% (4/4).
              </p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-gray-100 flex items-center gap-2 mb-1"><Globe className="w-4 h-4 text-cyan-400" /> API Docs</h3>
              <p className="text-sm text-gray-300">The full technical reference for both surfaces — every MCP tool/resource/prompt shape, and every REST endpoint (facade + admin), with copy-paste request examples.</p>
            </div>
          </div>
        </section>

        {/* Security & Best Practices */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <ShieldAlert className="w-6 h-6 text-red-400" /> Security & Best Practices
          </h2>
          <ul className="space-y-3">
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300">Data-layer failures surface as explicit errors (HTTP 503 on the REST facade, a raised <code className="bg-gray-900 px-1 rounded">RuntimeError</code> on the MCP tools) — AgentKit never fabricates KPI numbers when the database is unreachable.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300">The hosted SSE endpoint is bearer-token gated (<code className="bg-gray-900 px-1 rounded">MCP_AUTH_TOKEN</code>) with rate limiting; local stdio runs use your own credentials and never leave your machine.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300">Use a virtual environment (<code className="bg-gray-900 px-1 rounded">.venv</code>) when running the Python backend locally, and never commit <code className="bg-gray-900 px-1 rounded">.env</code> files or hardcode API keys — copy <code className="bg-gray-900 px-1 rounded">.env.example</code> and fill in your own.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300">The admin API's users/roles/audit-log/scenario endpoints (see API Docs) are an in-memory demo layer with no bundled UI — call them directly to exercise the REST facade. They reset on every process restart and are not the production auth system.</span>
            </li>
          </ul>
        </section>

      </div>
    </div>
  );
}

function ToolCard({ color, name, title, ask }: { color: string; name: string; title: string; ask: string }) {
  const colorMap: Record<string, string> = {
    green: "text-green-400", blue: "text-blue-400", red: "text-red-400",
    purple: "text-purple-400", yellow: "text-yellow-400", cyan: "text-cyan-400",
  };
  return (
    <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
      <h3 className={`font-semibold text-lg mb-1 ${colorMap[color]}`}>{title}</h3>
      <p className="text-xs font-mono text-gray-500 mb-2">{name}</p>
      <p className="text-sm text-gray-300">{ask}</p>
    </div>
  );
}
