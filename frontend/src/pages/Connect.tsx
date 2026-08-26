import { useState } from "react";
import { Cable, Check, Copy, TerminalSquare, Bot, Boxes } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip } from "../kit/primitives";

/* All snippets are real: claude_desktop_config.example.json (repo root) and demos/. */

// Same resolution order as ApiDocs.tsx/lib/api.ts: an explicit VITE_API_BASE_URL wins,
// otherwise same-origin — without this fallback the snippet below would render the
// literal string "undefined/sse" for anyone building without that env var set.
const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" ? window.location.origin : "");

const REMOTE_CONFIG = `{
  "mcpServers": {
    "agentkit-remote": {
      "command": "npx",
      "args": ["-y", "mcp-remote",
               "${BASE_URL}/sse",
               "--header",
               "Authorization: Bearer \${MCP_AUTH_TOKEN}"],
      "env": { "MCP_AUTH_TOKEN": "<your token>" }
    }
  }
}`;

const LOCAL_CONFIG = `{
  "mcpServers": {
    "agentkit-local": {
      "command": "/ABS/PATH/AgentKit/.venv/bin/python",
      "args": ["/ABS/PATH/AgentKit/mcp_server.py"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "POSTGRES_URL": "postgresql://...",
        "LLM_ENDPOINT": "https://api.openai.com/v1",
        "LLM_TOKEN": "sk-..."
      }
    }
  }
}`;

export default function Connect() {
  return (
    <div>
      <PageHeader
        title="Connect your agents"
        sub="Two direct integration paths: point Claude Desktop at the hosted SSE endpoint, or run the server locally over stdio. Custom declarative tool packs are loaded automatically."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Snippet
          icon={Cable}
          title="Claude Desktop — remote (hosted SSE)"
          tag="no local setup"
          note="Uses mcp-remote (Node). The hosted endpoint requires a bearer token (MCP_AUTH_TOKEN) — request one from the maintainer."
          code={REMOTE_CONFIG}
        />
        <Snippet
          icon={TerminalSquare}
          title="Claude Desktop — local (stdio)"
          tag="private"
          note="Runs on your machine with your own DB and keys; tools return explicit errors when POSTGRES_URL is missing."
          code={LOCAL_CONFIG}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="CrewAI demo" actions={<Chip><Bot size={11} /> demos/crewai_demo.py</Chip>}>
          <p className="text-[13px] leading-6 text-dim">
            A runnable CrewAI crew (planner / analyst / reporter) wired to the same service layer —
            production-validated against the live database. Run it from the repo:
          </p>
          <pre className="num mt-2 overflow-x-auto rounded-xl border border-line bg-bg p-3 font-mono text-[12px] leading-5 text-dim">python demos/crewai_demo.py</pre>
        </Card>
        <Card title="Claude Agent SDK demo" actions={<Chip><Boxes size={11} /> demos/claude_agent_sdk_demo.py</Chip>}>
          <p className="text-[13px] leading-6 text-dim">
            The same analyst pattern on Anthropic's Agent SDK — tool definitions map 1:1 onto the
            MCP tools, demonstrating that AgentKit's capability layer is framework-agnostic.
          </p>
          <pre className="num mt-2 overflow-x-auto rounded-xl border border-line bg-bg p-3 font-mono text-[12px] leading-5 text-dim">python demos/claude_agent_sdk_demo.py</pre>
        </Card>
      </div>
    </div>
  );
}

function Snippet({ icon: Icon, title, tag, note, code }: { icon: typeof Cable; title: string; tag: string; note: string; code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Card
      title={<span className="flex items-center gap-2"><Icon size={15} style={{ color: "var(--accent)" }} /> {title}</span>}
      actions={
        <div className="flex items-center gap-2">
          <Chip>{tag}</Chip>
          <button
            className="flex items-center gap-1 rounded-lg border border-line px-2 py-1 text-[11px] text-dim hover:text-body"
            onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
          >
            {copied ? <Check size={11} className="text-ok" /> : <Copy size={11} />} {copied ? "Copied" : "Copy"}
          </button>
        </div>
      }
    >
      <pre className="num overflow-x-auto rounded-xl border border-line bg-bg p-4 font-mono text-[12px] leading-6 text-dim">{code}</pre>
      <p className="mt-2 text-[12.5px] leading-5 text-muted">{note}</p>
    </Card>
  );
}
