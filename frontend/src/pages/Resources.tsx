import { useEffect, useState } from "react";
import { Database, MessageSquareQuote, RefreshCw } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState, Skeleton } from "../kit/primitives";
import { JSONViewer } from "../kit/JSONViewer";
import { api, isUnavailable, KPI } from "../lib/api";

/* The 6 kpi:// resources map 1:1 onto query_kpis(domain, limit=10) — the facade lets the
   browser read the same live values agents get. The prompt text below is the REAL template
   registered in mcp_server.py. */

const RESOURCES = ["Finance", "Growth", "Operations", "People", "ESG", "IT_Ops"];

const PROMPT_TEXT = `Produce a monthly executive briefing for {month}. Sections: KEY FINDING, EVIDENCE (from KPI tools), ROOT CAUSE, RECOMMENDED ACTION, RISK IF UNADDRESSED. Be concrete and concise.`;

export default function Resources() {
  return (
    <div>
      <PageHeader
        title="Resources & prompts"
        sub="MCP first-class citizens: live kpi:// resources and reusable prompt templates — exactly what a connected agent discovers."
      />
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {RESOURCES.map((d) => <ResourceCard key={d} domain={d} />)}
      </div>
      <Card
        title={<span className="flex items-center gap-2"><MessageSquareQuote size={15} style={{ color: "var(--accent)" }} /> monthly_executive_briefing</span>}
        className="mt-4"
        actions={<Chip>prompt template</Chip>}
      >
        <pre className="whitespace-pre-wrap rounded-xl border border-line bg-bg p-4 text-[12.5px] leading-6 text-dim">{PROMPT_TEXT}</pre>
        <p className="mt-2 text-[12.5px] text-muted">
          Registered in mcp_server.py — agents fill <code className="font-mono text-[11.5px]">{"{month}"}</code> and get a structured briefing spec.
        </p>
      </Card>
    </div>
  );
}

function ResourceCard({ domain }: { domain: string }) {
  const [kpis, setKpis] = useState<KPI[] | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "nodata" | "error">("loading");
  const [open, setOpen] = useState(false);

  const load = () => {
    setState("loading");
    api.kpis({ domain, limit: 10 })
      .then((r) => { setKpis(r.kpis); setState("ok"); })
      .catch((e) => setState(isUnavailable(e) ? "nodata" : "error"));
  };
  useEffect(load, [domain]);

  return (
    <Card
      title={<span className="num font-mono text-[12.5px]">kpi://{domain}/latest</span>}
      actions={<Button variant="ghost" onClick={load} aria-label="refresh"><RefreshCw size={13} /></Button>}
    >
      {state === "loading" ? (
        <Skeleton className="h-20" />
      ) : state === "nodata" ? (
        <EmptyState icon={Database} title="Data layer unavailable" />
      ) : state === "error" ? (
        <div className="text-[13px] text-bad">Failed to read resource</div>
      ) : kpis && kpis.length > 0 ? (
        <>
          <div className="space-y-1.5">
            {kpis.slice(0, open ? 10 : 4).map((k, i) => (
              <div key={i} className="flex items-center gap-2 text-[12.5px]">
                <span className="min-w-0 flex-1 truncate text-dim">{String(k.metric ?? "—")}</span>
                <span className="num font-semibold text-body">
                  {typeof k.value === "number" ? k.value.toLocaleString() : "—"}
                </span>
              </div>
            ))}
          </div>
          <button className="mt-2 text-[11.5px] text-muted underline decoration-dotted hover:text-body" onClick={() => setOpen((o) => !o)}>
            {open ? "less" : `all ${kpis.length}`}
          </button>
          {open && <div className="mt-2"><JSONViewer data={kpis} maxHeight={200} /></div>}
        </>
      ) : (
        <EmptyState title="No live values" />
      )}
    </Card>
  );
}
