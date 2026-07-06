import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Gauge, TriangleAlert, Wrench, BarChart3, GitBranch, DatabaseZap } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip, EmptyState, Skeleton, StatTile } from "../kit/primitives";
import { api, isUnavailable, Summary } from "../lib/api";

export default function Overview() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "nodata" | "error">("loading");
  const [errMsg, setErrMsg] = useState("");

  useEffect(() => {
    api.summary()
      .then((s) => { setSummary(s); setState("ok"); })
      .catch((e) => {
        setErrMsg(e instanceof Error ? e.message : String(e));
        setState(isUnavailable(e) ? "nodata" : "error");
      });
  }, []);

  return (
    <div>
      <PageHeader
        title="What would you like your agents to analyze today?"
        sub="AgentKit turns Claude Desktop, Cursor and custom agents into business analysts — six MCP tools with live PostgreSQL access. Everything below is the same data your agents see."
      />

      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        {[
          { to: "/tools", icon: Wrench, title: "Explore MCP tools", desc: "Six capability cards — run each one live." },
          { to: "/intelligence", icon: BarChart3, title: "Inspect KPIs", desc: "Domains, anomalies, forecasts on real data." },
          { to: "/workflow", icon: GitBranch, title: "Agent workflow", desc: "Planner, Analyst and Reporter pipeline." },
        ].map((a) => (
          <Link key={a.to} to={a.to} className="group">
            <Card hover className="h-full">
              <a.icon size={18} style={{ color: "var(--accent)" }} strokeWidth={1.7} />
              <div className="mt-2 text-sm font-semibold text-body group-hover:underline group-hover:decoration-dotted">{a.title}</div>
              <p className="mt-1 text-[12.5px] leading-5 text-dim">{a.desc}</p>
            </Card>
          </Link>
        ))}
      </div>

      {state === "loading" ? (
        <div className="grid gap-4 sm:grid-cols-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : state === "nodata" ? (
        <Card>
          <EmptyState
            icon={DatabaseZap}
            title="Data layer unavailable on this instance"
            hint={`The tools return explicit errors rather than fabricated data: "${errMsg}". Set POSTGRES_URL with the seeded kpi_metrics table to enable this page.`}
          />
        </Card>
      ) : state === "error" ? (
        <Card><div className="text-sm text-bad">{errMsg}</div></Card>
      ) : summary && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatTile
              label="Company health"
              value={summary.health_score.toFixed(1)}
              sub={summary.interpretation}
              icon={Gauge}
              delta={{ text: summary.interpretation, good: summary.health_score >= 60 }}
            />
            <StatTile label="Key metrics tracked" value={summary.key_metrics.length} sub="top KPIs in snapshot" icon={Activity} />
            <StatTile
              label="Active anomalies"
              value={summary.anomalies.length}
              icon={TriangleAlert}
              delta={summary.anomalies.length > 0 ? { text: "investigate", good: false } : { text: "all clear" }}
            />
          </div>

          {Object.keys(summary.components).length > 0 && (
            <Card title="Health components" className="mt-4">
              <div className="grid gap-3 sm:grid-cols-4">
                {Object.entries(summary.components).map(([k, v]) => (
                  <div key={k} className="rounded-xl border border-line bg-surface-2 p-3.5">
                    <div className="text-[11px] font-medium uppercase tracking-wide text-muted">{k.replace("_", " ")}</div>
                    <div className="num mt-1 text-lg font-bold text-body">{typeof v === "number" ? v.toFixed(1) : String(v)}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card title="Key metrics" className="mt-4" actions={<Chip>from get_executive_summary</Chip>}>
            {summary.key_metrics.length === 0 ? (
              <EmptyState title="No metrics in snapshot" />
            ) : (
              <div className="divide-y divide-[var(--border)]">
                {summary.key_metrics.map((m, i) => (
                  <div key={i} className="flex items-center gap-3 py-2.5">
                    <span className="min-w-0 flex-1 truncate text-sm text-body">{String(m.metric ?? "—")}</span>
                    {m.category != null && <Chip>{String(m.category)}</Chip>}
                    {m.period != null && <Chip className="num">{String(m.period)}</Chip>}
                    <span className="num text-sm font-semibold text-body">
                      {typeof m.value === "number" ? m.value.toLocaleString() : String(m.value ?? "—")}
                      {m.unit ? <span className="ml-1 text-muted">{String(m.unit)}</span> : null}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
