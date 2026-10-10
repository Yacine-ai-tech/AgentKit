import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Bot, FileText, ListChecks, Wrench, Play, Download, AlertTriangle } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState } from "../kit/primitives";
import { ExecutionStages } from "../kit/misc";
import { AgentGraph } from "../kit/AgentGraph";
import { JSONViewer } from "../kit/JSONViewer";
import { api, WorkflowResult } from "../lib/api";

/* v1 "Workflow" — the real LangGraph pipeline (workflow.py) plus a LIVE run: POST
   /api/workflow/run executes planner → analyst → reporter against live data and
   returns the plan, tool calls and executive report (exportable). */

const AGENTS = [
  { icon: ListChecks, name: "Planner", fn: "planner_agent", role: "Breaks the question into an analysis plan: which KPIs to pull, which tools to call." },
  { icon: Wrench, name: "Analyst", fn: "analyst_agent", role: "Executes the plan against live PostgreSQL through the same functions the MCP tools expose." },
  { icon: FileText, name: "Reporter", fn: "reporter_agent", role: "Synthesizes the evidence into an executive-ready report with findings and actions." },
];

export default function Workflow() {
  const [question, setQuestion] = useState("Why did revenue move last quarter, and what should we watch?");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [err, setErr] = useState("");

  const run = async () => {
    setBusy(true); setErr(""); setResult(null);
    try { setResult(await api.runWorkflow(question)); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  const exportReport = () => {
    if (!result) return;
    const md = [
      `# AgentKit Executive Report`,
      `\n**Question:** ${result.question}\n`,
      result.plan ? `## Plan\n${result.plan}\n` : "",
      result.report ? `## Report\n${result.report}\n` : "",
      ...(result.report_sections ? Object.entries(result.report_sections).map(([k, v]) => `## ${k}\n${v}\n`) : []),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([md], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url; a.download = "agentkit-report.md"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <PageHeader
        title="Agent workflow"
        sub="A real LangGraph pipeline: three specialized agents sharing one typed state, from question to executive report. Run it live below."
      />

      <Card title="Run a live analysis" actions={<Chip><Bot size={11} /> spends LLM credits</Chip>}>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-0 flex-1">
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2}
              className="w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 text-sm text-body outline-none focus:border-[var(--accent)]" />
          </div>
          <Button onClick={run} disabled={busy || !question.trim()}>
            <Play size={14} /> {busy ? "Running…" : "Run workflow"}
          </Button>
        </div>
        {busy && (
          <div className="mt-4">
            <ExecutionStages stages={["Planner — building the analysis plan", "Analyst — querying live data via tools", "Reporter — synthesizing the executive report"]} active={1} />
            <div className="mt-2 text-[12px] text-muted">
              This runs a real 3-agent pipeline against live data — typically 20-30s, longer if the
              inference backend needs to wake from idle.
            </div>
          </div>
        )}
        {err && <div className="mt-3 flex items-start gap-2 text-[13px] text-bad"><AlertTriangle size={14} className="mt-0.5" />{err}</div>}
      </Card>

      {result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-4 space-y-4">
          {/* Status & Export Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-surface-1 border border-line rounded-xl">
            <div className="flex items-center gap-2">
              <Chip tone={result.error ? "bad" : "ok"}>
                {result.error ? "Execution Error" : "Analysis Complete"}
              </Chip>
              {result._elapsed_ms != null && (
                <Chip className="num">{(result._elapsed_ms / 1000).toFixed(1)}s total runtime</Chip>
              )}
            </div>
            <Button variant="secondary" onClick={exportReport}>
              <Download size={13} /> Export Executive Report (.md)
            </Button>
          </div>

          {/* Stage 1: Analysis Plan */}
          {result.plan && (
            <Card
              title="Stage 1 — Planner Agent Analysis Strategy"
              actions={<Chip className="bg-blue-500/10 text-blue-400 border-blue-500/30">Planner Agent</Chip>}
            >
              <div className="p-4 bg-surface-2 rounded-xl border border-line">
                <p className="whitespace-pre-wrap text-[13.5px] leading-7 text-body font-mono">
                  {result.plan}
                </p>
              </div>
            </Card>
          )}

          {/* Stage 2 & 3: Executive Synthesis */}
          {result.report && (
            <Card
              title="Stage 2 & 3 — Executive Briefing & Synthesis"
              actions={<Chip tone="accent">Reporter Agent</Chip>}
            >
              <div className="prose prose-invert max-w-none text-[13.5px] leading-7 text-body p-4 bg-surface-2 rounded-xl border border-line whitespace-pre-wrap font-sans">
                {result.report}
              </div>
            </Card>
          )}

          {/* Structured Report Findings */}
          {result.report_sections && Object.keys(result.report_sections).length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-body tracking-wide uppercase text-dim">
                Detailed Analysis Breakdown
              </h3>
              <div className="grid gap-4 lg:grid-cols-2">
                {Object.entries(result.report_sections).map(([k, v]) => (
                  <Card
                    key={k}
                    title={k.toUpperCase()}
                    className="border-line hover:border-line-strong transition"
                  >
                    <p className="whitespace-pre-wrap text-[13px] leading-6 text-dim">{v}</p>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Execution Telemetry & Raw State */}
          <Card title="Pipeline Execution Audit & Raw State">
            <JSONViewer data={result} maxHeight={320} />
          </Card>
        </motion.div>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
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

      <Card title="Agent Studio Visualization" className="mt-4">
        <AgentGraph />
      </Card>

      {!result && !busy && (
        <Card className="mt-4">
          <EmptyState icon={FileText} title="No run yet" hint="Ask a business question above and run the three-agent workflow against live data." />
        </Card>
      )}
    </div>
  );
}
