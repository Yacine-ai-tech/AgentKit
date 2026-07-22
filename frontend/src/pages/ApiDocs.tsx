import { useState } from "react";
import { Terminal, Copy, Check, Code2, BookOpen, Zap, Shield, Globe } from "lucide-react";

const BASE_URL = "https://gateway.ysiddo-ai-projects.app/agentkit";

const ENDPOINTS = [
  {
    method: "GET", path: "/health", desc: "Health check — verify the service is alive.",
    response: `{"status":"ok","service":"agentkit","version":"0.1.0"}`,
    body: null,
  },
  {
    method: "POST", path: "/agents/run", desc: "Execute an autonomous agent task with tool-use.",
    body: JSON.stringify({ task: "Summarize Q3 sales data and identify top 3 anomalies", tools: ["calculator", "web_search"], model: "gemini-2.0-flash" }, null, 2),
    response: `{"task_id":"agt_xyz","status":"completed","result":"...","steps":[...],"tokens_used":1240}`,
  },
  {
    method: "GET", path: "/agents/{task_id}", desc: "Poll a running agent task by ID.",
    body: null,
    response: `{"task_id":"agt_xyz","status":"running","progress":0.6}`,
  },
  {
    method: "POST", path: "/mcp/invoke", desc: "Invoke an MCP (Model Context Protocol) tool directly.",
    body: JSON.stringify({ tool: "calculator", input: { expression: "42 * 1.15" } }, null, 2),
    response: `{"result":48.3,"tool":"calculator","latency_ms":12}`,
  },
  {
    method: "GET", path: "/sse", desc: "Server-Sent Events stream — real-time agent step updates.",
    body: null,
    response: `data: {"step":1,"type":"tool_call","tool":"web_search"}\ndata: {"step":2,"type":"result","output":"..."}`,
  },
];

const SNIPPETS: Record<string, (ep: (typeof ENDPOINTS)[0]) => string> = {
  curl: (ep: any) =>
    ep.body
      ? `curl -X ${ep.method} "${BASE_URL}${ep.path}" \\\n  -H "Content-Type: application/json" \\\n  -d '${ep.body}'`
      : `curl "${BASE_URL}${ep.path}"`,
  python: (ep: any) =>
    ep.body
      ? `import requests\n\nresp = requests.${ep.method.toLowerCase()}(\n  "${BASE_URL}${ep.path}",\n  json=${ep.body.replace(/"/g, "'")}\n)\nprint(resp.json())`
      : `import requests\n\nresp = requests.get("${BASE_URL}${ep.path}")\nprint(resp.json())`,
  node: (ep: any) =>
    ep.body
      ? `const res = await fetch("${BASE_URL}${ep.path}", {\n  method: "${ep.method}",\n  headers: { "Content-Type": "application/json" },\n  body: JSON.stringify(${ep.body})\n});\nconst data = await res.json();\nconsole.log(data);`
      : `const res = await fetch("${BASE_URL}${ep.path}");\nconst data = await res.json();\nconsole.log(data);`,
};

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  return (
    <button onClick={copy} style={{ background: "none", border: "none", cursor: "pointer", color: copied ? "#4ade80" : "#94a3b8", padding: "4px" }}>
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

function CodeBlock({ code }: { code: string }) {
  return (
    <div style={{ position: "relative", background: "rgba(0,0,0,0.4)", borderRadius: 8, padding: "14px 40px 14px 14px", fontFamily: "monospace", fontSize: "0.78rem", color: "#e2e8f0", whiteSpace: "pre-wrap", wordBreak: "break-all", lineHeight: 1.6 }}>
      <div style={{ position: "absolute", top: 8, right: 8 }}><CopyBtn text={code} /></div>
      {code}
    </div>
  );
}

export default function ApiDocs() {
  const [lang, setLang] = useState<"curl" | "python" | "node">("curl");
  const [active, setActive] = useState(0);
  const ep = ENDPOINTS[active];

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1100, color: "#e2e8f0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <Terminal size={28} color="#a78bfa" />
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0 }}>AgentKit API Reference</h1>
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#94a3b8" }}>Integrate autonomous AI agents into your systems in minutes</p>
        </div>
      </div>

      {/* Info banners */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, margin: "20px 0" }}>
        {[
          { icon: Globe, label: "Base URL", value: BASE_URL, color: "#38bdf8" },
          { icon: Shield, label: "Auth", value: "Bearer token (header)", color: "#4ade80" },
          { icon: Zap, label: "Protocol", value: "REST + SSE streaming", color: "#f59e0b" },
          { icon: BookOpen, label: "Format", value: "JSON in, JSON out", color: "#a78bfa" },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 10, padding: "12px 16px", display: "flex", gap: 10, alignItems: "center" }}>
            <Icon size={18} color={color} />
            <div><div style={{ fontSize: "0.7rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div><div style={{ fontSize: "0.85rem", fontWeight: 600 }}>{value}</div></div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 20 }}>
        {/* Endpoint list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: "0.7rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>Endpoints</div>
          {ENDPOINTS.map((e, i) => (
            <button key={i} onClick={() => setActive(i)} style={{ textAlign: "left", background: active === i ? "rgba(124,58,237,0.15)" : "rgba(255,255,255,0.03)", border: active === i ? "1px solid rgba(124,58,237,0.4)" : "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: "10px 14px", cursor: "pointer", transition: "all .15s" }}>
              <span style={{ fontSize: "0.68rem", fontWeight: 700, fontFamily: "monospace", background: e.method === "GET" ? "rgba(56,189,248,0.15)" : "rgba(167,139,250,0.15)", color: e.method === "GET" ? "#38bdf8" : "#a78bfa", borderRadius: 4, padding: "2px 6px", marginRight: 8 }}>{e.method}</span>
              <span style={{ fontSize: "0.8rem", fontFamily: "monospace", color: active === i ? "#e2e8f0" : "#94a3b8" }}>{e.path}</span>
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: "16px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, fontFamily: "monospace", background: ep.method === "GET" ? "rgba(56,189,248,0.15)" : "rgba(167,139,250,0.15)", color: ep.method === "GET" ? "#38bdf8" : "#a78bfa", borderRadius: 5, padding: "3px 8px" }}>{ep.method}</span>
              <code style={{ fontSize: "0.9rem", color: "#e2e8f0" }}>{BASE_URL}{ep.path}</code>
            </div>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "#94a3b8" }}>{ep.desc}</p>
          </div>

          {ep.body && (
            <div>
              <div style={{ fontSize: "0.75rem", color: "#64748b", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}><Code2 size={13} /> Request body</div>
              <CodeBlock code={ep.body} />
            </div>
          )}

          <div>
            <div style={{ display: "flex", gap: 6, marginBottom: 8, alignItems: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b", marginRight: 4 }}>Language:</span>
              {(["curl", "python", "node"] as const).map((l) => (
                <button key={l} onClick={() => setLang(l)} style={{ padding: "4px 12px", borderRadius: 6, border: "1px solid", borderColor: lang === l ? "#7c3aed" : "rgba(255,255,255,0.1)", background: lang === l ? "rgba(124,58,237,0.2)" : "transparent", color: lang === l ? "#c4b5fd" : "#94a3b8", cursor: "pointer", fontSize: "0.78rem", fontWeight: 600 }}>{l}</button>
              ))}
            </div>
            <CodeBlock code={(SNIPPETS as any)[lang](ep)} />
          </div>

          <div>
            <div style={{ fontSize: "0.75rem", color: "#64748b", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}><Check size={13} color="#4ade80" /> Sample response</div>
            <CodeBlock code={ep.response} />
          </div>
        </div>
      </div>
    </div>
  );
}
