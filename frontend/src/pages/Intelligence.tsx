import { useEffect, useMemo, useState } from "react";
import * as Recharts from "recharts";
const { ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, } = Recharts;
import { ArrowDownRight, ArrowUpRight, DatabaseZap, TrendingUp, TriangleAlert } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip, EmptyState, Skeleton } from "../kit/primitives";
import { Label, Select } from "../kit/misc";
import { api, Anomalies, DOMAINS, Forecast, isUnavailable, KPI } from "../lib/api";

export default function Intelligence() {
  const [domain, setDomain] = useState("Finance");
  const [kpis, setKpis] = useState<KPI[] | null>(null);
  const [metrics, setMetrics] = useState<string[]>([]);
  const [anoms, setAnoms] = useState<Anomalies | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "nodata" | "error">("loading");
  const [errMsg, setErrMsg] = useState("");

  useEffect(() => {
    setState("loading"); setKpis(null); setAnoms(null);
    Promise.all([api.kpis({ domain, limit: 200 }), api.metrics(domain), api.anomalies(domain)])
      .then(([k, m, a]) => { setKpis(k.kpis); setMetrics(m.metrics); setAnoms(a); setState("ok"); })
      .catch((e) => { setErrMsg(String(e?.message ?? e)); setState(isUnavailable(e) ? "nodata" : "error"); });
  }, [domain]);

  return (
    <div>
      <PageHeader
        title="Business intelligence"
        sub="The same live PostgreSQL data your agents query — grouped by domain, with anomaly detection and Monte-Carlo-banded forecasts."
        actions={
          <Select value={domain} onChange={setDomain} options={DOMAINS.map((d) => ({ value: d, label: d }))} />
        }
      />

      {state === "loading" ? (
        <Skeleton className="h-80 w-full" />
      ) : state === "nodata" ? (
        <Card>
          <EmptyState icon={DatabaseZap} title="Data layer unavailable on this instance"
            hint={`"${errMsg}" — set POSTGRES_URL with the seeded kpi_metrics table.`} />
        </Card>
      ) : state === "error" ? (
        <Card><div className="text-sm text-bad">{errMsg}</div></Card>
      ) : (
        <>
          <KPITable kpis={kpis ?? []} />
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <AnomalyCard anoms={anoms} />
            <ForecastCard metrics={metrics} />
          </div>
        </>
      )}
    </div>
  );
}

function KPITable({ kpis }: { kpis: KPI[] }) {
  const byMetric = useMemo(() => {
    const m = new Map<string, KPI[]>();
    kpis.forEach((k) => {
      const key = String(k.metric ?? "—");
      m.set(key, [...(m.get(key) ?? []), k]);
    });
    return [...m.entries()].map(([metric, rows]) => ({
      metric,
      rows: rows.sort((a, b) => String(a.period).localeCompare(String(b.period))),
    }));
  }, [kpis]);

  if (kpis.length === 0) return <Card><EmptyState title="No KPIs in this domain" /></Card>;

  return (
    <Card title={`${byMetric.length} metrics · ${kpis.length} datapoints`} noPad className="overflow-hidden">
      <div className="max-h-[380px] divide-y divide-[var(--border)] overflow-y-auto">
        {byMetric.map(({ metric, rows }) => {
          const latest = rows[rows.length - 1];
          const prev = rows[rows.length - 2];
          const delta = prev && typeof latest.value === "number" && typeof prev.value === "number" && prev.value !== 0
            ? ((latest.value - prev.value) / Math.abs(prev.value)) * 100 : null;
          return (
            <div key={metric} className="flex items-center gap-3 px-5 py-2.5">
              <span className="min-w-0 flex-1 truncate text-sm text-body">{metric}</span>
              <Spark rows={rows} />
              {latest.period != null && <Chip className="num">{String(latest.period)}</Chip>}
              <span className="num w-28 text-right text-sm font-semibold text-body">
                {typeof latest.value === "number" ? latest.value.toLocaleString() : "—"}
                {latest.unit ? <span className="ml-1 text-[11px] font-normal text-muted">{String(latest.unit)}</span> : null}
              </span>
              <span className={`num inline-flex w-16 items-center justify-end gap-0.5 text-[12px] ${delta == null ? "text-muted" : delta >= 0 ? "text-ok" : "text-bad"}`}>
                {delta == null ? "—" : <>{delta >= 0 ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}{Math.abs(delta).toFixed(1)}%</>}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function Spark({ rows }: { rows: KPI[] }) {
  const vals = rows.map((r) => (typeof r.value === "number" ? r.value : 0));
  if (vals.length < 2) return <span className="w-20" />;
  const min = Math.min(...vals), max = Math.max(...vals), range = max - min || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * 76},${18 - ((v - min) / range) * 16}`).join(" ");
  return (
    <svg width="80" height="20" className="shrink-0 opacity-80">
      <polyline points={pts} fill="none" stroke="var(--accent)" strokeWidth="1.5" />
    </svg>
  );
}

function AnomalyCard({ anoms }: { anoms: Anomalies | null }) {
  return (
    <Card title="Anomalies" actions={anoms && <Chip className="num">z ≥ {anoms.threshold}</Chip>}>
      {!anoms || anoms.anomalies.length === 0 ? (
        <EmptyState icon={TriangleAlert} title="No anomalies at this threshold" hint="detect_kpi_anomalies found nothing unusual in this domain's history." />
      ) : (
        <div className="max-h-[300px] space-y-2 overflow-y-auto pr-1">
          {anoms.anomalies.map((a, i) => (
            <div key={i} className="flex items-center gap-3 rounded-xl border border-line bg-[rgba(255,107,107,0.05)] px-3.5 py-2.5">
              <TriangleAlert size={14} className="shrink-0 text-bad" />
              <span className="min-w-0 flex-1 truncate text-[13px] text-body">{String(a.metric ?? "—")}</span>
              {a.period != null ? <Chip className="num">{String(a.period)}</Chip> : null}
              <span className="num text-[13px] text-dim">{typeof a.value === "number" ? a.value.toLocaleString() : "—"}</span>
              {typeof a.z_score === "number" && <Chip tone="bad" className="num">z {a.z_score.toFixed(1)}</Chip>}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function ForecastCard({ metrics }: { metrics: string[] }) {
  const [metric, setMetric] = useState("");
  const [fc, setFc] = useState<Forecast | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { if (metrics.length && !metric) setMetric(metrics[0]); }, [metrics, metric]);

  useEffect(() => {
    if (!metric) return;
    setBusy(true); setErr(""); setFc(null);
    api.forecast(metric).then(setFc).catch((e) => setErr(String(e?.message ?? e))).finally(() => setBusy(false));
  }, [metric]);

  const data = useMemo(() => (fc?.forecast ?? []).map((p, i) => ({
    period: p.period, value: p.value, lo: fc?.lower_ci[i], hi: fc?.upper_ci[i],
  })), [fc]);

  return (
    <Card title="Forecast" actions={fc?.method && fc.method !== "none" && <Chip>{fc.method}</Chip>}>
      <div className="mb-3">
        <Label>Metric</Label>
        <Select value={metric} onChange={setMetric} options={metrics.map((m) => ({ value: m, label: m }))} className="w-full" />
      </div>
      {busy ? (
        <Skeleton className="h-48" />
      ) : err ? (
        <div className="text-[13px] text-bad">{err}</div>
      ) : !fc || !Array.isArray(data) || data.length === 0 ? (
        <EmptyState icon={TrendingUp} title="No forecast" hint={fc?.note === "insufficient_history" ? "Not enough history for this metric." : "Pick a metric with history."} />
      ) : (
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "var(--text-muted)", fontSize: 10.5 }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
              <YAxis tick={{ fill: "var(--text-muted)", fontSize: 10.5 }} axisLine={false} tickLine={false} width={58} />
              <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border-strong)", borderRadius: 12, color: "var(--text)", fontSize: 12 }} />
              <Area dataKey="hi" stroke="none" fill="var(--accent)" fillOpacity={0.1} isAnimationActive={false} />
              <Area dataKey="lo" stroke="none" fill="var(--bg)" fillOpacity={1} isAnimationActive={false} />
              <Line dataKey="value" stroke="var(--accent)" strokeWidth={2} dot={{ r: 2.5 }} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
      {fc && data.length > 0 && (
        <p className="num mt-2 text-[11.5px] text-muted">
          {fc.confidence_level != null ? `${(fc.confidence_level * 100).toFixed(0)}% confidence band · ` : ""}{data.length} periods ahead
        </p>
      )}
    </Card>
  );
}
