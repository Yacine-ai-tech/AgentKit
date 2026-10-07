import React, { useState } from 'react';
import {
  ShieldCheck, Brain, Wrench, Activity, CheckCircle2,
  Terminal, Layers, BarChart3, AlertCircle, FileCode, Clock
} from 'lucide-react';
import { PageHeader } from '../kit/AppShell';
import { Card, Button, StatTile } from '../kit/primitives';
import { Link } from 'react-router-dom';

const GUARDRAIL_RESULTS = [
  { guardrail: 'Write switch', adversarial: 'Write tool invoked with AGENTKIT_ALLOW_WRITES=false', outcome: 'Deny (writes_disabled)', status: 'Passed' },
  { guardrail: 'Scope authorization', adversarial: 'Caller lacks tool-required scope', outcome: 'Deny (missing_scope)', status: 'Passed' },
  { guardrail: 'Approval token absent', adversarial: 'Destructive tool invoked without token', outcome: 'Deny (approval_required)', status: 'Passed' },
  { guardrail: 'Approval token invalid', adversarial: 'Destructive tool invoked with tampered token', outcome: 'Deny (approval_required)', status: 'Passed' },
  { guardrail: 'Approval unconfigured', adversarial: 'Destructive tool invoked when secret unset', outcome: 'Deny (approval_unavailable)', status: 'Passed' },
  { guardrail: 'Per-tool rate limit', adversarial: 'Tool invoked beyond burst limit window', outcome: 'Deny (rate_limited)', status: 'Passed' },
  { guardrail: 'Dry-run preflight', adversarial: 'Destructive call executed with dry_run=true', outcome: 'Permit simulation, no DB commit', status: 'Passed' },
  { guardrail: 'Audit logging (allowed)', adversarial: 'Normal authorized tool call', outcome: 'Emitted to structured telemetry log', status: 'Passed' },
  { guardrail: 'Audit logging (denied)', adversarial: 'Any security policy violation', outcome: 'Emitted with denial reason & caller IP', status: 'Passed' },
];

const DOMAIN_RESULTS = [
  { domain: 'Finance', scenarios: 5, passed: 5, coverage: '100%' },
  { domain: 'People (HR)', scenarios: 4, passed: 4, coverage: '100%' },
  { domain: 'Operations', scenarios: 4, passed: 4, coverage: '100%' },
  { domain: 'Customer', scenarios: 4, passed: 4, coverage: '100%' },
  { domain: 'Engineering', scenarios: 4, passed: 4, coverage: '100%' },
  { domain: 'Growth', scenarios: 3, passed: 3, coverage: '100%' },
  { domain: 'Logistics', scenarios: 3, passed: 3, coverage: '100%' },
  { domain: 'ESG', scenarios: 3, passed: 3, coverage: '100%' },
  { domain: 'IT Operations', scenarios: 3, passed: 3, coverage: '100%' },
  { domain: 'Security Posture', scenarios: 3, passed: 3, coverage: '100%' },
  { domain: 'Cross-Domain Multi-Tool', scenarios: 7, passed: 7, coverage: '100%' },
];

const MCP_TOOL_METRICS = [
  { metric: 'Tool Selection Accuracy', score: '12 / 12 (100%)', benchmark: 'Semantic intent alignment' },
  { metric: 'Tool Execution Success Rate', score: '12 / 12 (100%)', benchmark: 'Zero unhandled protocol faults' },
  { metric: 'Average Execution Time', score: '26.87 s', benchmark: 'Full generation cycle with LLM synthesis' },
  { metric: 'P95 Execution Latency', score: '39.86 s', benchmark: 'Complex multi-hop cross-domain analysis' },
  { metric: 'Report Quality Score', score: '12 / 12 (100%)', benchmark: 'Executive completeness verification' },
];

export default function BenchmarkPage() {
  const [activeTab, setActiveTab] = useState<'guardrails' | 'langgraph' | 'mcp'>('guardrails');

  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto space-y-8">
      <PageHeader
        title="AgentKit — Empirical Benchmark Suite"
        sub="Deterministic policy guardrails, LangGraph multi-domain reasoning, and live MCP protocol performance metrics."
        actions={
          <div className="flex gap-2">
            <Link to="/research">
              <Button variant="secondary">
                <Brain size={14} className="mr-1 inline" /> Research Architecture
              </Button>
            </Link>
          </div>
        }
      />

      {/* Headline Stat Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="Policy Guardrails"
          value="14 / 14"
          sub="Deterministic policy tests"
          delta={{ text: "100% enforced" }}
          icon={ShieldCheck}
        />
        <StatTile
          label="LangGraph Orchestration"
          value="43 / 43"
          sub="Multi-domain agent scenarios"
          delta={{ text: "100% pass rate" }}
          icon={Brain}
        />
        <StatTile
          label="MCP Tool Selection"
          value="12 / 12"
          sub="Reference BI pack queries"
          delta={{ text: "100% accuracy" }}
          icon={Wrench}
        />
        <StatTile
          label="Protocol Overhead"
          value="< 1.2 ms"
          sub="JSON-RPC serialization latency"
          icon={Clock}
        />
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2 border-b border-line pb-3">
        <button
          onClick={() => setActiveTab('guardrails')}
          className={`px-4 py-2 rounded-btn text-xs font-medium transition-colors ${
            activeTab === 'guardrails' ? 'bg-surface-2 text-body border border-line-strong' : 'text-dim hover:text-body'
          }`}
        >
          1. Policy Guardrails (14/14)
        </button>
        <button
          onClick={() => setActiveTab('langgraph')}
          className={`px-4 py-2 rounded-btn text-xs font-medium transition-colors ${
            activeTab === 'langgraph' ? 'bg-surface-2 text-body border border-line-strong' : 'text-dim hover:text-body'
          }`}
        >
          2. LangGraph Multi-Domain (43/43)
        </button>
        <button
          onClick={() => setActiveTab('mcp')}
          className={`px-4 py-2 rounded-btn text-xs font-medium transition-colors ${
            activeTab === 'mcp' ? 'bg-surface-2 text-body border border-line-strong' : 'text-dim hover:text-body'
          }`}
        >
          3. MCP Tool Performance (12/12)
        </button>
      </div>

      {/* Tab 1: Policy Guardrails */}
      {activeTab === 'guardrails' && (
        <Card title="Primary Security Benchmark: Protocol-Level Capability Invariants">
          <p className="text-xs text-dim mb-4 leading-relaxed">
            Evaluates whether the capability policy engine correctly denies out-of-policy invocations and records each event. The suite runs 100% deterministically with zero network calls or external LLM dependencies.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-line text-left text-muted font-medium uppercase tracking-wider">
                  <th className="pb-2.5 pr-4">Policy Guardrail</th>
                  <th className="pb-2.5 pr-4">Adversarial Trigger Condition</th>
                  <th className="pb-2.5 pr-4">Enforced Behavior</th>
                  <th className="pb-2.5 text-right">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {GUARDRAIL_RESULTS.map((row) => (
                  <tr key={row.guardrail}>
                    <td className="py-2.5 pr-4 font-semibold text-body">{row.guardrail}</td>
                    <td className="py-2.5 pr-4 text-dim">{row.adversarial}</td>
                    <td className="py-2.5 pr-4 font-mono text-[11px] text-accent">{row.outcome}</td>
                    <td className="py-2.5 text-right font-semibold text-ok">
                      <span className="inline-flex items-center gap-1">
                        <CheckCircle2 size={13} /> {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Tab 2: LangGraph Orchestration */}
      {activeTab === 'langgraph' && (
        <Card title="LangGraph Multi-Domain Agent Evaluation (43/43 Passed)">
          <p className="text-xs text-dim mb-4 leading-relaxed">
            The three-node LangGraph agent (Planner → Analyst → Reporter) was tested on 43 standardized scenarios spanning all 10 corporate KPI domains and complex cross-domain multi-tool queries.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-line text-left text-muted font-medium uppercase tracking-wider">
                    <th className="pb-2">Domain</th>
                    <th className="pb-2 text-center">Scenarios</th>
                    <th className="pb-2 text-center">Passed</th>
                    <th className="pb-2 text-right">Coverage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {DOMAIN_RESULTS.map((row) => (
                    <tr key={row.domain}>
                      <td className="py-2 font-medium text-body">{row.domain}</td>
                      <td className="py-2 text-center text-dim">{row.scenarios}</td>
                      <td className="py-2 text-center font-semibold text-ok">{row.passed}</td>
                      <td className="py-2 text-right font-semibold text-ok">{row.coverage}</td>
                    </tr>
                  ))}
                  <tr className="font-bold border-t border-line text-body">
                    <td className="py-2.5">Total Suite</td>
                    <td className="py-2.5 text-center">43</td>
                    <td className="py-2.5 text-center text-ok">43</td>
                    <td className="py-2.5 text-right text-ok">100.0%</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="space-y-3">
              <div className="rounded-xl border border-line bg-surface-2 p-4 text-xs text-dim">
                <div className="font-semibold text-body mb-1">Cross-Domain Multi-Tool Synthesis</div>
                <p className="leading-relaxed">
                  Seven complex queries specifically test cross-domain tool orchestration (e.g., comparing HR headcount trends with financial gross margin expansion). All 7 scenarios invoked both required tools in the correct topological sequence and grounded reports accurately.
                </p>
              </div>

              <div className="rounded-xl border border-line bg-surface-2 p-4 text-xs text-dim">
                <div className="font-semibold text-body mb-1">High-Throughput Groq LPU Validation</div>
                <p className="leading-relaxed">
                  Evaluated with Groq LPU inference matching production reasoning performance. Validates deterministic keyword tool routing and robust synthesis across enterprise BI domains.
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Tab 3: MCP Tool Performance */}
      {activeTab === 'mcp' && (
        <Card title="Reference MCP BI Tool Performance Suite (12 Scenarios)">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-line text-left text-muted font-medium uppercase tracking-wider">
                  <th className="pb-2.5 pr-4">Evaluation Metric</th>
                  <th className="pb-2.5 pr-4">Measured Score</th>
                  <th className="pb-2.5">Methodology & Standard</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {MCP_TOOL_METRICS.map((row) => (
                  <tr key={row.metric}>
                    <td className="py-2.5 pr-4 font-semibold text-body">{row.metric}</td>
                    <td className="py-2.5 pr-4 font-bold text-accent">{row.score}</td>
                    <td className="py-2.5 text-dim">{row.benchmark}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* CLI Reproduction */}
      <Card title="CLI Reproducibility Commands">
        <div className="rounded-lg bg-surface-2 p-4 font-mono text-xs space-y-2 border border-line text-accent">
          <div className="text-muted"># 1. Run deterministic policy guardrails test suite</div>
          <div className="text-body">pytest tests/test_policy_guardrails.py -v</div>
          <div className="text-muted pt-2"># 2. Run LangGraph 43-scenario multi-domain evaluation</div>
          <div className="text-body">python eval/run_dspy_eval.py</div>
          <div className="text-muted pt-2"># 3. Run live MCP tool selection and execution benchmark</div>
          <div className="text-body">python eval/run_mcp_tools_benchmark.py</div>
        </div>
      </Card>
    </div>
  );
}
