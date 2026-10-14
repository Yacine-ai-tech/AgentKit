import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity, Award, BookOpen, Boxes, Brain, Cable, Cloud, Cog, Cpu, Database, FileText, Filter,
  Gauge, GitBranch, Globe, Layers, Lock, Mic, Network, Pause, Play, Radio, RadioTower, Scale,
  Search, ShieldCheck, Sigma, Sparkles, Terminal, Wrench, Workflow, Zap, type LucideIcon,
} from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip } from "../kit/primitives";
import { PipelineFlow, type Stage } from "../kit/PipelineFlow";

const ICONS: Record<string, LucideIcon> = {
  Activity, Award, BookOpen, Boxes, Brain, Cable, Cloud, Cog, Cpu, Database, FileText, Filter,
  Gauge, GitBranch, Globe, Layers, Lock, Mic, Network, Radio, RadioTower, Scale, Search,
  ShieldCheck, Sigma, Sparkles, Terminal, Wrench, Workflow, Zap,
};

type NodeInfo = { id: string; label: string; layer: string; icon: string; summary: string; detail: string[]; env?: string[] };
type StageInfo = { id: string; label: string; icon: string; text: string; nodes: string[] };
type Arch = {
  title: string; sub: string; lifecycleTitle: string; layers: string[]; nodes: NodeInfo[]; stages: StageInfo[];
  endpoints: [string, string][]; decisions: [string, string][]; links: { to: string; label: string }[];
};

const DATA: Arch = {
  "title": "Architecture",
  "sub": "How AgentKit lets agents call business tools under one policy, with a record of every decision.",
  "lifecycleTitle": "Life of a tool call",
  "layers": [
    "Clients",
    "Governance",
    "Tools",
    "Intelligence"
  ],
  "nodes": [
    {
      "id": "mcp",
      "label": "MCP server",
      "layer": "Clients",
      "icon": "Network",
      "summary": "SSE or stdio transport for Claude Desktop, Cursor, Devin and custom agents.",
      "detail": [
        "Bearer-token auth and a per-client rate limit on the SSE endpoint.",
        "Six built-in read tools, resources and prompts."
      ],
      "env": [
        "MCP_TRANSPORT",
        "MCP_PORT",
        "MCP_AUTH_TOKEN",
        "MCP_RATE_LIMIT"
      ]
    },
    {
      "id": "rest",
      "label": "REST facade",
      "layer": "Clients",
      "icon": "GitBranch",
      "summary": "The same tools as HTTP endpoints, plus policy, audit and routing views.",
      "detail": [
        "Used by the dashboard and any HTTP caller.",
        "Optional internal-token gate on every /api route."
      ],
      "env": [
        "REQUIRE_INTERNAL_TOKEN",
        "AGENTKIT_INTERNAL_TOKEN"
      ]
    },
    {
      "id": "policy",
      "label": "Policy engine",
      "layer": "Governance",
      "icon": "ShieldCheck",
      "summary": "One enforcement point for every caller, independent of the agent framework.",
      "detail": [
        "Order: unknown tool, writes disabled, missing scope, destructive without approval, rate limit; a dry run is simulated.",
        "Fails closed: a default install cannot mutate anything.",
        "The approval token is held by a human, never by the model."
      ],
      "env": [
        "AGENTKIT_ALLOW_WRITES",
        "AGENTKIT_SCOPES",
        "AGENTKIT_APPROVAL_TOKEN"
      ]
    },
    {
      "id": "audit",
      "label": "Audit trail",
      "layer": "Governance",
      "icon": "FileText",
      "summary": "A record before execution and an outcome after.",
      "detail": [
        "A crash still leaves the decision on record.",
        "Optional JSON Lines sink for durable storage."
      ],
      "env": [
        "AGENTKIT_AUDIT_LOG"
      ]
    },
    {
      "id": "builtin",
      "label": "Built-in KPI tools",
      "layer": "Tools",
      "icon": "Gauge",
      "summary": "Query KPIs, company health, anomalies, forecast, metrics, executive summary.",
      "detail": [
        "Read-only, registered with the same policy engine as every other tool."
      ],
      "env": [
        "POSTGRES_URL"
      ]
    },
    {
      "id": "packs",
      "label": "Tool packs (YAML)",
      "layer": "Tools",
      "icon": "Boxes",
      "summary": "Define tools over a Postgres or HTTP source without writing Python.",
      "detail": [
        "Parameters are bound by the driver, never interpolated.",
        "Credentials come from a named environment variable.",
        "Effects and scopes are declared by the pack author."
      ],
      "env": [
        "AGENTKIT_PACKS"
      ]
    },
    {
      "id": "router",
      "label": "LLM router",
      "layer": "Intelligence",
      "icon": "Brain",
      "summary": "Tiered routing with a self-hosted tier and provider fallbacks.",
      "detail": [
        "default, reasoning, judge and local tiers.",
        "Rate limits retry; authentication errors switch to the configured fallback."
      ],
      "env": [
        "LLM_DEFAULT",
        "LLM_REASONING",
        "LLM_JUDGE",
        "INFERENCE_MODE",
        "LLM_FALLBACK_TO_LOCAL"
      ]
    },
    {
      "id": "workflow",
      "label": "LangGraph workflow",
      "layer": "Intelligence",
      "icon": "Workflow",
      "summary": "Planner, analyst and reporter agents over the tools.",
      "detail": [
        "Planner and reporter use the reasoning tier; the analyst calls tools on the default tier."
      ]
    }
  ],
  "stages": [
    {
      "id": "auth",
      "label": "Authenticate",
      "icon": "Lock",
      "text": "Bearer token on SSE, internal token on the REST facade.",
      "nodes": [
        "mcp",
        "rest"
      ]
    },
    {
      "id": "decide",
      "label": "Decide",
      "icon": "ShieldCheck",
      "text": "Policy checks run in a fixed order; the decision is final before anything executes.",
      "nodes": [
        "policy"
      ]
    },
    {
      "id": "record",
      "label": "Record",
      "icon": "FileText",
      "text": "The pending decision is written first, so a crash cannot erase it.",
      "nodes": [
        "audit"
      ]
    },
    {
      "id": "run",
      "label": "Execute",
      "icon": "Zap",
      "text": "Built-in tools read the KPI store; pack tools run bound SQL or an HTTP call, or simulate for a dry run.",
      "nodes": [
        "builtin",
        "packs"
      ]
    },
    {
      "id": "out",
      "label": "Return",
      "icon": "Activity",
      "text": "The outcome is recorded and JSON is returned; denials map to 403, bad input to 422.",
      "nodes": [
        "audit",
        "rest"
      ]
    }
  ],
  "endpoints": [
    [
      "MCP /sse, stdio",
      "Model Context Protocol transport"
    ],
    [
      "GET /api/tools",
      "Tool catalogue with effects and parameters"
    ],
    [
      "GET /api/resources",
      "Resources"
    ],
    [
      "GET /api/prompts/{name}",
      "Prompts"
    ],
    [
      "GET /api/kpis",
      "Query KPIs for a domain and period window"
    ],
    [
      "GET /api/health-score",
      "Composite company health"
    ],
    [
      "GET /api/anomalies",
      "Anomaly detection"
    ],
    [
      "GET /api/forecast",
      "Forecast a metric"
    ],
    [
      "GET /api/metrics",
      "Available metrics"
    ],
    [
      "GET /api/summary",
      "Executive summary"
    ],
    [
      "GET /api/policy",
      "Capability envelope: effects, scopes, switches"
    ],
    [
      "GET /api/audit",
      "Allowed and denied calls with reasons"
    ],
    [
      "GET /api/llm-routing",
      "Resolved model for each tier"
    ],
    [
      "GET /api/packs",
      "Loaded tool packs"
    ],
    [
      "GET /api/observability",
      "Operational counters"
    ],
    [
      "POST /api/workflow/run",
      "Run the planner, analyst, reporter workflow"
    ],
    [
      "GET /health",
      "Liveness"
    ]
  ],
  "decisions": [
    [
      "Policy lives with the tool",
      "LangGraph, CrewAI, the Claude Agent SDK and raw MCP clients all get identical enforcement."
    ],
    [
      "Fail closed, audit first",
      "Nothing mutates by default, and every decision is recorded before it is acted on."
    ],
    [
      "Declared, bound, additive",
      "Effects are declared, parameters are bound, and packs add tools without changing the originals."
    ]
  ],
  "links": [
    {
      "to": "/research",
      "label": "Research"
    },
    {
      "to": "/benchmark",
      "label": "Benchmarks"
    }
  ]
};

export default function ArchitecturePage() {
  const [selected, setSelected] = useState<string>(DATA.nodes[0].id);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [filter, setFilter] = useState("");

  const stages: (Stage & { text: string; nodes: string[] })[] = useMemo(
    () => DATA.stages.map((s) => ({ ...s, icon: ICONS[s.icon] ?? Zap })), []);

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setStep((s) => (s + 1) % (stages.length + 1)), 1800);
    return () => clearInterval(t);
  }, [playing, stages.length]);

  const current = stages[Math.min(step, stages.length - 1)];
  const lit = useMemo(() => new Set(step < stages.length ? current.nodes : []), [step, current, stages.length]);
  const node = DATA.nodes.find((n) => n.id === selected) ?? DATA.nodes[0];
  const endpoints = DATA.endpoints.filter(([r, p]) => (r + " " + p).toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto space-y-8">
      <PageHeader
        title={DATA.title}
        sub={DATA.sub}
        actions={
          <div className="flex gap-2">
            {DATA.links.map((l) => (
              <Link key={l.to} to={l.to}><Button variant="secondary">{l.label}</Button></Link>
            ))}
          </div>
        }
      />

      <Card title={DATA.lifecycleTitle}>
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs text-dim">Pick a stage or let it play; the components involved are highlighted below.</div>
          <Button variant="secondary" onClick={() => setPlaying((p) => !p)}>
            {playing ? <Pause size={14} className="mr-1 inline" /> : <Play size={14} className="mr-1 inline" />}
            {playing ? "Pause" : "Play"}
          </Button>
        </div>
        <PipelineFlow stages={stages} active={step} done={step >= stages.length} />
        <div className="mt-3 flex flex-wrap gap-2">
          {stages.map((s, i) => (
            <button key={s.id} onClick={() => { setPlaying(false); setStep(i); }}
              className={`rounded-lg border px-3 py-1 text-xs ${i === step ? "border-accent text-body" : "border-line text-dim"}`}>
              {i + 1}. {s.label}
            </button>
          ))}
        </div>
        <p className="mt-3 text-sm text-dim">{step < stages.length ? current.text : "Complete."}</p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {DATA.layers.map((layer) => (
            <Card key={layer} title={layer}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {DATA.nodes.filter((n) => n.layer === layer).map((n) => {
                  const Icon = ICONS[n.icon] ?? Boxes;
                  const active = selected === n.id;
                  return (
                    <button key={n.id} onClick={() => setSelected(n.id)}
                      className={`text-left rounded-xl border p-3 transition-colors ${active ? "border-accent bg-surface-2" : "border-line bg-surface"} ${lit.has(n.id) ? "ring-1 ring-accent" : ""}`}>
                      <div className="flex items-center gap-2 text-sm font-semibold text-body"><Icon size={14} /> {n.label}</div>
                      <div className="mt-1 text-xs text-dim">{n.summary}</div>
                    </button>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>

        <Card title={node.label} className="h-fit lg:sticky lg:top-4">
          <p className="text-sm text-dim">{node.summary}</p>
          <ul className="mt-3 space-y-2 text-xs text-dim list-disc pl-4">
            {node.detail.map((d) => <li key={d}>{d}</li>)}
          </ul>
          {node.env && node.env.length > 0 && (
            <div className="mt-4">
              <div className="text-[11px] uppercase tracking-wider text-muted mb-1">Configuration</div>
              <div className="flex flex-wrap gap-1.5">{node.env.map((e) => <Chip key={e}>{e}</Chip>)}</div>
            </div>
          )}
        </Card>
      </div>

      <Card title="Interfaces">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter routes…"
          aria-label="Filter routes"
          className="w-full mb-3 rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs text-body outline-none focus:border-accent"
        />
        <div className="divide-y divide-line text-xs">
          {endpoints.map(([r, p]) => (
            <div key={r} className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4 py-2">
              <code className="sm:w-72 shrink-0 text-body">{r}</code>
              <span className="text-dim">{p}</span>
            </div>
          ))}
          {endpoints.length === 0 && <div className="py-3 text-dim">No route matches.</div>}
        </div>
      </Card>

      <Card title="Design decisions">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-dim">
          {DATA.decisions.map(([t, d]) => (
            <div key={t} className="rounded-xl border border-line bg-surface-2 p-4">
              <div className="font-semibold text-body text-sm mb-1">{t}</div>{d}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
