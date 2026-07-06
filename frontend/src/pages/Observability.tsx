import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Pause, Play, Gauge, AlertTriangle } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip, EmptyState, StatTile } from "../kit/primitives";
import { api, ObsRequest } from "../lib/api";

/* v1 "Observability" — real facade request telemetry (method, path, status, latency)
   from the in-memory ring the server records for every /api call. */

export default function Observability() {
  const [reqs, setReqs] = useState<ObsRequest[] | null>(null);
  const [paused, setPaused] = useState(false);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useEffect(() => {
    let alive = true;
    const tick = () => api.observability(150).then((r) => { if (alive && !pausedRef.current) setReqs(r.requests); }).catch(() => {});
    tick();
    const t = setInterval(tick, 2500);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const stats = useMemo(() => {
    const r = reqs ?? [];
    const errs = r.filter((x) => x.status >= 400).length;
    const avg = r.length ? r.reduce((a, x) => a + x.ms, 0) / r.length : 0;
    return { total: r.length, errs, avg };
  }, [reqs]);

  return (
    <div>
      <PageHeader
        title="Observability"
        sub="Every call to the tool facade is traced — method, path, status and latency — so you can watch your agents work in real time."
        actions={
          <button className="flex items-center gap-1.5 rounded-btn border border-line-strong px-3 py-2 text-sm text-body hover:bg-surface-2" onClick={() => setPaused((p) => !p)}>
            {paused ? <Play size={13} /> : <Pause size={13} />} {paused ? "Resume" : "Pause"}
          </button>
        }
      />
      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <StatTile label="Traced requests" value={stats.total} icon={Activity} sub="in-memory window" />
        <StatTile label="Errors" value={stats.errs} icon={AlertTriangle}
          delta={stats.errs ? { text: "review", good: false } : { text: "all 2xx/3xx" }} />
        <StatTile label="Avg latency" value={`${stats.avg.toFixed(0)} ms`} icon={Gauge} />
      </div>
      <Card title="Request trace" noPad className="overflow-hidden">
        {!reqs ? (
          <div className="p-5"><EmptyState icon={Activity} title="Connecting…" /></div>
        ) : reqs.length === 0 ? (
          <EmptyState icon={Activity} title="No requests traced yet" hint="Run a tool or open Business Intelligence — calls appear here instantly." />
        ) : (
          <div className="max-h-[540px] divide-y divide-[var(--border)] overflow-y-auto">
            <AnimatePresence initial={false}>
              {reqs.map((r, i) => (
                <motion.div key={`${r.ts}-${i}`} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                  className="grid grid-cols-[52px_1fr_64px_70px] items-center gap-3 px-4 py-2.5 text-[12.5px]">
                  <Chip tone="accent">{r.method}</Chip>
                  <span className="min-w-0 truncate font-mono text-dim">{r.path}{r.query ? `?${r.query}` : ""}</span>
                  <Chip tone={r.status >= 400 ? "bad" : "ok"} className="num justify-self-start">{r.status}</Chip>
                  <span className="num justify-self-end text-muted">{r.ms} ms</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </Card>
    </div>
  );
}
