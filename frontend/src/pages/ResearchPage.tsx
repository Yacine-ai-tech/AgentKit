import React from 'react';
import {
  ShieldAlert, Brain, Wrench, Lock, Activity, BookOpen,
  CheckCircle2, Terminal, Layers, ArrowRight, ExternalLink,
  Cpu, FileCode, GitBranch, Scale
} from 'lucide-react';
import { PageHeader } from '../kit/AppShell';
import { Card, Button } from '../kit/primitives';
import { Link } from 'react-router-dom';

export default function ResearchPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto space-y-8">
      <PageHeader
        title="AgentKit — Architectural & Security Research"
        sub="Typed capability policy enforcement, protocol-level boundaries, and stateful DAG orchestration for LLM agent systems."
        actions={
          <div className="flex gap-2">
            <Link to="/benchmark">
              <Button variant="primary">
                <Activity size={14} className="mr-1 inline" /> View Benchmarks
              </Button>
            </Link>
            <Link to="/user-guide">
              <Button variant="secondary">
                <BookOpen size={14} className="mr-1 inline" /> User Guide
              </Button>
            </Link>
          </div>
        }
      />

      {/* Executive Abstract */}
      <Card title="Abstract & Engineering Contribution" className="bg-surface/80">
        <p className="text-dim leading-relaxed text-sm mb-4">
          AgentKit is an open-source <strong className="text-body">Model Context Protocol (MCP)</strong> server implementing a deterministic capability policy engine for governed LLM tool execution. Its primary engineering contribution is the enforcement of typed effect policies at the protocol layer — below the agent and independent of prompt content — ensuring that the reachable action set is bounded by deployment configuration regardless of what an LLM is persuaded to attempt via adversarial prompt injection.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="rounded-xl border border-line bg-surface-2 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-accent mb-1">Protocol Boundary</div>
            <div className="font-semibold text-body text-sm mb-1">Below-the-Prompt Security</div>
            <div className="text-xs text-dim">Enforcement runs in the Python runtime before tool dispatch, so it does not depend on the model complying with a prompt.</div>
          </div>
          <div className="rounded-xl border border-line bg-surface-2 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-ok mb-1">Stateful Graph</div>
            <div className="font-semibold text-body text-sm mb-1">LangGraph 3-Node DAG</div>
            <div className="font-semibold text-xs text-dim">Hierarchical Planner → Analyst → Reporter workflow orchestrating multi-domain tool chains.</div>
          </div>
          <div className="rounded-xl border border-line bg-surface-2 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">Dual Transport</div>
            <div className="font-semibold text-body text-sm mb-1">Stdio & Authenticated SSE</div>
            <div className="text-xs text-dim">Standard stdio pipe for local dev (Cursor, Claude Desktop) and token-gated SSE for hosted agent swarms.</div>
          </div>
        </div>
      </Card>

      {/* Problem Formulation: The MCP Security Gap */}
      <Card title="1. Context: The MCP Security Gap">
        <div className="space-y-4 text-sm text-dim leading-relaxed">
          <p>
            The Model Context Protocol (Anthropic, 2024) provides standardized discovery and execution of external tools. However, prevalent MCP implementations entrust authorization entirely to system prompt instructions. In practice, prompt-level controls fail under adversarial conditions:
          </p>
          <ul className="list-disc pl-5 space-y-2 text-dim text-xs">
            <li><strong className="text-body">Indirect Prompt Injection:</strong> Retrieved untrusted context, user inputs, and intermediary tool outputs share the LLM attention window with system instructions.</li>
            <li><strong className="text-body">Absence of Caller Scopes:</strong> Conventional servers treat all invocations identically without granular capability scopes.</li>
            <li><strong className="text-body">Binary Permissioning:</strong> Destructive operations are either permanently permitted or globally disabled, with no dry-run simulation or human-held approval token.</li>
          </ul>
          <div className="rounded-lg border border-bad/30 bg-bad/10 p-4 text-xs text-bad flex items-start gap-3">
            <ShieldAlert size={18} className="shrink-0 mt-0.5" />
            <div>
              <strong>Security Invariant:</strong> Security policies must reside at the protocol boundary as deterministic invariants, not as advisory prompts to stochastic language models.
            </div>
          </div>
        </div>
      </Card>

      {/* Mathematical & Architectural Specification */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="2. Typed Effect Policies">
          <div className="space-y-3 text-xs text-dim leading-relaxed">
            <p>
              Each registered tool <code className="text-accent">t ∈ T</code> carries a formal policy envelope:
            </p>
            <div className="rounded-lg bg-surface-2 p-3 font-mono text-[11px] text-body border border-line">
              PolicyEnvelope = (EffectType, RequiredScope, RateLimit, RequiresApproval, SupportsDryRun)
            </div>
            <p>
              Effect types are strictly partitioned into three categories:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li><strong className="text-body">Read-Only:</strong> Safe queries without state mutation (e.g., <code className="text-accent">get_company_health</code>).</li>
              <li><strong className="text-body">Write:</strong> Controlled updates governed by rate limits.</li>
              <li><strong className="text-body">Destructive:</strong> Gated by a human-held approval token, with dry-run preflight available.</li>
            </ul>
          </div>
        </Card>

        <Card title="3. LangGraph Orchestration Topology">
          <div className="space-y-3 text-xs text-dim leading-relaxed">
            <p>
              AgentKit implements a hierarchical three-node directed acyclic graph (DAG):
            </p>
            <div className="rounded-lg bg-surface-2 p-3 font-mono text-[11px] text-body border border-line space-y-1">
              <div>[User Query] → [Planner Node]</div>
              <div className="pl-6">↓ Decompose into domain subtasks</div>
              <div className="pl-4">→ [Analyst Node] (Tools invoked via MCP Policy)</div>
              <div className="pl-6">↓ Synthesize telemetry & metrics</div>
              <div className="pl-4">→ [Reporter Node] → [Structured Report]</div>
            </div>
            <p>
              State is strictly typed across graph transitions, enabling deterministic auditing and mid-flight recovery.
            </p>
          </div>
        </Card>
      </div>

      {/* DSPy Pipeline Optimization */}
      <Card title="4. DSPy Pipeline Optimization & Empirical Validation">
        <div className="space-y-4 text-sm text-dim leading-relaxed">
          <p>
            In addition to manual prompt engineering, AgentKit incorporates a DSPy compilation harness (<code className="text-accent">research/dspy_experiment.py</code>) casting the multi-domain reasoning agent as declarative Signatures:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-lg bg-surface-2 p-3.5 border border-line">
              <div className="font-semibold text-body text-xs mb-1">Uncompiled Baseline</div>
              <div className="text-xs text-dim">Direct zero-shot prompting over tool descriptions. Held-out score 0.680 on 30 hand-written business questions.</div>
            </div>
            <div className="rounded-lg bg-surface-2 p-3.5 border border-line">
              <div className="font-semibold text-body text-xs mb-1">BootstrapFewShot Compiled</div>
              <div className="text-xs text-dim">Compiled demonstrations select few-shot exemplars automatically. Held-out score 0.707 on the same 30 questions: a small gain, not a categorical improvement.</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Academic Citations */}
      <Card title="5. Academic Literature & References">
        <div className="space-y-3 text-xs text-dim">
          <div className="border-b border-line pb-2">
            <div className="font-semibold text-body">Securing the Model Context Protocol: Defending LLMs Against Tool Poisoning and Adversarial Attacks</div>
            <div className="text-muted">arXiv:2512.06556 (2025). Layered defences against tool poisoning at the descriptor and runtime level.</div>
          </div>
          <div className="border-b border-line pb-2">
            <div className="font-semibold text-body">Breaking the Protocol: Security Analysis of the Model Context Protocol</div>
            <div className="text-muted">Maloyan, N. and Namiot, D. arXiv:2601.17549 (2026). Argues the weaknesses are architectural, including missing capability attestation.</div>
          </div>
          <div className="border-b border-line pb-2">
            <div className="font-semibold text-body">DSPy: Compiling Declarative Language Model Calls into State-of-the-Art Pipelines</div>
            <div className="text-muted">Khattab, O., et al. (2023; ICLR 2024). The framework behind the compilation experiment.</div>
          </div>
          <div className="border-b border-line pb-2">
            <div className="font-semibold text-body">LangGraph documentation</div>
            <div className="text-muted">LangChain (2024–2026). The state-graph library used for the planner, analyst and reporter workflow.</div>
          </div>
          <div>
            <div className="font-semibold text-body">Model Context Protocol Specification</div>
            <div className="text-muted">Anthropic and contributors (2024–2026). The open standard for local and remote tool connectivity.</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
