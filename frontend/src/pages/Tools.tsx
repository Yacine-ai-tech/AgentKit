import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Play, Wrench, AlertTriangle } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState, Skeleton } from "../kit/primitives";
import { JSONViewer } from "../kit/JSONViewer";
import { api, isUnavailable, ToolMeta } from "../lib/api";

export default function Tools() {
  const [tools, setTools] = useState<ToolMeta[] | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.tools().then((t) => setTools(t.tools)).catch((e) => setErr(String(e)));
  }, []);

  return (
    <div>
      <PageHeader
        title="MCP tools"
        sub="The six capabilities your agents get. Each card runs the exact function the MCP tool executes — same code path, same live database."
      />
      {err && <Card><div className="text-sm text-bad">{err}</div></Card>}
      {!tools ? (
        <div className="grid gap-4 lg:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-48" />)}</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {tools.map((t) => <ToolCard key={t.name} tool={t} />)}
        </div>
      )}
    </div>
  );
}

function ToolCard({ tool }: { tool: ToolMeta }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState("");
  const [unavailable, setUnavailable] = useState(false);

  const run = async () => {
    setBusy(true); setErr(""); setResult(null); setUnavailable(false);
    try {
      const params: Record<string, string | number | undefined> = {};
      tool.params.forEach((p) => {
        const v = values[p.name];
        if (v !== undefined && v !== "") params[p.name === "metric_name" ? "metric" : p.name] = v;
      });
      setResult(await api.run(tool.endpoint, params));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setUnavailable(isUnavailable(e));
    } finally { setBusy(false); }
  };

  return (
    <Card
      title={<span className="font-mono text-[13px]">{tool.name}</span>}
      actions={<Chip>{tool.endpoint}</Chip>}
    >
      <p className="text-[13px] leading-6 text-dim">{tool.description}</p>

      {tool.params.length > 0 && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {tool.params.map((p) => (
            <label key={p.name} className="block">
              <span className="mb-1 block text-[10.5px] font-medium uppercase tracking-wide text-muted">
                {p.name}{p.required ? " *" : ""}{p.default !== undefined ? ` (default ${String(p.default)})` : ""}
              </span>
              <input
                value={values[p.name] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [p.name]: e.target.value }))}
                placeholder={p.type}
                className="w-full rounded-input border border-line-strong bg-surface-2 px-2.5 py-1.5 text-[12.5px] text-body outline-none focus:border-[var(--accent)]"
              />
            </label>
          ))}
        </div>
      )}

      <div className="mt-3">
        <Button onClick={run} disabled={busy}>
          <Play size={13} /> {busy ? "Running…" : "Run tool"}
        </Button>
      </div>

      {err && (
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-line bg-surface-2 p-3 text-[12.5px] leading-5 text-dim">
          {unavailable ? <Wrench size={14} className="mt-0.5 shrink-0 text-warn" /> : <AlertTriangle size={14} className="mt-0.5 shrink-0 text-bad" />}
          <span>{unavailable ? `Data layer unavailable — the tool returned an explicit error: ${err}` : err}</span>
        </div>
      )}
      {result && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-3">
          <JSONViewer data={result} maxHeight={260} />
        </motion.div>
      )}
      {!result && !err && !busy && (
        <div className="mt-3"><EmptyState title="Not run yet" hint="Fill optional parameters (or none) and execute." /></div>
      )}
    </Card>
  );
}
