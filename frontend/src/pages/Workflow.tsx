import { ArrowRight, Bot, FileText, ListChecks, Wrench } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip } from "../kit/primitives";

/* Factual page: the pipeline below is the real LangGraph workflow in workflow.py
   (planner_agent → analyst_agent → reporter_agent over BusinessAnalysisState).
   No simulated runs are shown — executing the workflow spends LLM credits and is a
   CLI/agent concern; this page documents the real structure and how to run it. */

const AGENTS = [
  {
    icon: ListChecks,
    name: "Planner",
    fn: "planner_agent",
    role: "Breaks the business question into an analysis plan: which KPIs to pull, which tools to call, what to look for.",
  },
  {
    icon: Wrench,
    name: "Analyst",
    fn: "analyst_agent",
    role: "Executes the plan against live PostgreSQL through the same functions the MCP tools expose — KPIs, health, anomalies, forecasts.",
  },
  {
    icon: FileText,
    name: "Reporter",
    fn: "reporter_agent",
    role: "Synthesizes the evidence into an executive-ready summary with findings and recommended actions.",
  },
];

export default function Workflow() {
  return (
    <div>
      <PageHeader
        title="Agent workflow"
        sub="A real LangGraph pipeline (workflow.py): three specialized agents sharing one typed state, from question to executive report."
      />

      <Card title="Execution pipeline">
        <div className="flex flex-wrap items-center gap-2 py-1 text-[13px] text-dim">
          {["Question", "Planning", "Tool selection", "Data retrieval", "Analysis", "Reporting"].map((s, i, arr) => (
            <span key={s} className="flex items-center gap-2">
              <span className={`rounded-lg border px-2.5 py-1 ${i > 0 && i < arr.length - 1 ? "border-line" : "border-[var(--accent)] text-body"}`}>{s}</span>
              {i < arr.length - 1 && <ArrowRight size={13} className="text-muted" />}
            </span>
          ))}
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {AGENTS.map((a, i) => (
          <Card key={a.fn} hover>
            <div className="flex items-center justify-between">
              <a.icon size={20} style={{ color: "var(--accent)" }} strokeWidth={1.6} />
              <Chip className="num">step {i + 1}</Chip>
            </div>
            <div className="mt-3 text-[15px] font-semibold text-body">{a.name}</div>
            <div className="num mt-0.5 font-mono text-[11px] text-muted">workflow.py · {a.fn}</div>
            <p className="mt-3 text-[13px] leading-6 text-dim">{a.role}</p>
          </Card>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Shared state" actions={<Chip>BusinessAnalysisState</Chip>}>
          <p className="text-[13px] leading-6 text-dim">
            The agents communicate through a single typed LangGraph state — the question, the plan,
            retrieved KPI evidence, and the final report accumulate as the graph advances. That makes
            every run inspectable: each stage's contribution is a named field, not a hidden prompt.
          </p>
        </Card>
        <Card title="Run it" actions={<Chip><Bot size={11} /> spends LLM credits</Chip>}>
          <pre className="num overflow-x-auto rounded-xl border border-line bg-bg p-4 font-mono text-[12px] leading-6 text-dim">{`# from the AgentKit repo (needs POSTGRES_URL + LLM keys)
python -c "from workflow import analyze; \\
print(analyze('Why did Q2 revenue spike?'))"`}</pre>
          <p className="mt-2 text-[12.5px] leading-5 text-muted">
            The same three-agent pattern also ships as runnable CrewAI and Claude-Agent-SDK demos —
            see the Connect page.
          </p>
        </Card>
      </div>
    </div>
  );
}
