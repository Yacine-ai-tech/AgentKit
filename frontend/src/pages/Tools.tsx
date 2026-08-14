import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Play, Wrench, AlertTriangle, ShieldAlert, ShieldCheck } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState, Skeleton } from "../kit/primitives";
import { JSONViewer } from "../kit/JSONViewer";
import { api, isUnavailable, ToolMeta, PolicyResponse, ToolPolicy } from "../lib/api";

export default function Tools() {
  const [tools, setTools] = useState<ToolMeta[] | null>(null);
  const [policy, setPolicy] = useState<PolicyResponse | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api.tools(), api.policy()])
      .then(([t, p]) => {
        setTools(t.tools);
        setPolicy(p);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div>
      <PageHeader
        title="MCP tools"
        sub="The capabilities your agents get. Each card runs the exact function the MCP tool executes, gated by the policy engine."
      />
      {err && <Card><div className="text-sm text-bad">{err}</div></Card>}
      
      {policy && (
        <div className="mb-6 rounded-xl border border-line bg-surface-1 p-4 flex gap-6 text-[13px]">
          <div className="flex items-center gap-2">
            {policy.writes_enabled ? <ShieldAlert className="text-warn" size={16}/> : <ShieldCheck className="text-good" size={16}/>}
            <span className="text-dim">Writes:</span>
            <span className="font-medium text-body">{policy.writes_enabled ? "ENABLED" : "DISABLED"}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-dim">Approval:</span>
            <span className="font-medium text-body">{policy.approval_configured ? "CONFIGURED" : "NOT SET"}</span>
          </div>
        </div>
      )}

      {!tools ? (
        <div className="grid gap-4 lg:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-48" />)}</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {tools.map((t) => (
            <ToolCard 
              key={t.name} 
              tool={t} 
              policy={policy?.tools?.[t.name]} 
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ToolCard({ tool, policy }: { tool: ToolMeta; policy?: ToolPolicy }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [dryRun, setDryRun] = useState(false);
  const [approvalToken, setApprovalToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState("");
  const [unavailable, setUnavailable] = useState(false);

  // Tools from api/tools might have effect/scopes, but if policy exists it is more authoritative.
  const effect = policy?.effect || tool.effect || "read";
  const scopes = policy?.scopes || tool.scopes || [];

  const run = async () => {
    setBusy(true); setErr(""); setResult(null); setUnavailable(false);
    try {
      const params: Record<string, string | number | undefined> = {};
      tool.params.forEach((p) => {
        const v = values[p.name];
        if (v !== undefined && v !== "") params[p.name === "metric_name" ? "metric" : p.name] = v;
      });
      if (effect !== "read") {
        if (dryRun) params.dry_run = "true";
        if (approvalToken) params.approval_token = approvalToken;
      }
      setResult(await api.run(tool.endpoint, params));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setUnavailable(isUnavailable(e));
    } finally { setBusy(false); }
  };

  const getEffectColor = (eff: string) => {
    if (eff === "destructive") return "bg-bad/20 text-bad border-bad/30";
    if (eff === "write") return "bg-warn/20 text-warn border-warn/30";
    return "bg-good/20 text-good border-good/30";
  };

  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          <span className="font-mono text-[13px]">{tool.name}</span>
          <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${getEffectColor(effect)}`}>
            {effect}
          </span>
        </div>
      }
      actions={<Chip>{tool.endpoint}</Chip>}
    >
      <p className="text-[13px] leading-6 text-dim">{tool.description}</p>
      
      {scopes.length > 0 && (
        <div className="mt-2 text-[11px] text-muted flex gap-2">
          <span>Scopes:</span>
          {scopes.map(s => <span key={s} className="px-1 bg-surface-3 rounded">{s}</span>)}
        </div>
      )}

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

      {effect !== "read" && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
           <label className="block flex items-center gap-2 mt-4 cursor-pointer">
              <input 
                type="checkbox" 
                checked={dryRun} 
                onChange={(e) => setDryRun(e.target.checked)}
                className="rounded border-line-strong bg-surface-2"
              />
              <span className="text-[11px] font-medium uppercase tracking-wide text-muted">Dry Run</span>
           </label>
           
           {(policy?.requires_approval || effect === "destructive") && (
             <label className="block">
                <span className="mb-1 block text-[10.5px] font-medium uppercase tracking-wide text-muted">Approval Token *</span>
                <input
                  type="password"
                  value={approvalToken}
                  onChange={(e) => setApprovalToken(e.target.value)}
                  placeholder="Supervisor token"
                  className="w-full rounded-input border border-line-strong bg-surface-2 px-2.5 py-1.5 text-[12.5px] text-body outline-none focus:border-[var(--accent)]"
                />
             </label>
           )}
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
