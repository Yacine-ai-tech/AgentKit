import React from 'react';
import { BookOpen, Monitor, Terminal, FileCode, CheckCircle, ShieldAlert } from 'lucide-react';

export default function UserGuidePage() {
  return (
    <div className="p-8 max-w-5xl mx-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-8">
        <BookOpen className="w-10 h-10 text-blue-500" />
        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
          AgentKit Intelligence - User Guide
        </h1>
      </div>

      <p className="text-lg text-gray-300 mb-8 leading-relaxed">
        AgentKit provides advanced Model Context Protocol (MCP) servers to allow your agents to execute code, browse the web, and manage files autonomously.
      </p>

      <div className="space-y-8 text-gray-200">
        
        {/* Core Features Section */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Monitor className="w-6 h-6 text-green-400" /> Interface & Features Walkthrough
          </h2>
          <div className="space-y-4">
            
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-blue-400 text-lg mb-2">1. MCP Tools</h3>
              <p className="text-sm text-gray-300">Interact directly with underlying MCP servers to execute shell commands, manage code, and read files.</p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-purple-400 text-lg mb-2">2. Business Intelligence</h3>
              <p className="text-sm text-gray-300">Monitor your agent's execution DAGs and workflows across complex tasks.</p>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-amber-400 text-lg mb-2">3. Overview Dashboard</h3>
              <p className="text-sm text-gray-300">Track agent health, memory usage, and tool execution success rates in real-time.</p>
            </div>
          </div>
        </section>

        {/* Integration Setup Section */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Terminal className="w-6 h-6 text-orange-400" /> Integration & Setup Instructions
          </h2>
          
            <div>
              <h3 className="font-semibold text-lg text-gray-100 flex items-center gap-2 mb-2">
                <FileCode className="w-5 h-5 text-gray-400" /> Claude Desktop Integration
              </h3>
              <p className="text-sm text-gray-300 mb-3">To use AgentKit as an MCP server in Claude Desktop, add the following to your `claude_desktop_config.json`:</p>
              <pre className="bg-gray-950 p-4 rounded-lg text-sm font-mono text-green-300 overflow-x-auto">
{`{
  "mcpServers": {
    "agentkit-mcp": {
      "command": "python",
      "args": ["-m", "agentkit.mcp"],
      "env": {
        "OPENAI_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}`}
              </pre>
            </div>

            <div className="mt-6">
              <h3 className="font-semibold text-lg text-gray-100 flex items-center gap-2 mb-2">
                <FileCode className="w-5 h-5 text-gray-400" /> Cursor Setup
              </h3>
              <p className="text-sm text-gray-300 mb-3">To enable these capabilities in Cursor IDE:</p>
              <ul className="list-disc list-inside text-sm text-gray-300 space-y-2 ml-2">
                <li>Open Cursor Settings <code className="bg-gray-900 px-1 rounded">Cmd + Shift + J</code></li>
                <li>Navigate to <strong>Features</strong> &gt; <strong>MCP Servers</strong></li>
                <li>Click <strong>+ Add New MCP Server</strong></li>
                <li>Set type to <code>command</code>, name to <strong>AgentKit</strong>, and command to <code>python -m agentkit.mcp</code></li>
              </ul>
            </div>
        </section>

        {/* Security & Best Practices */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <ShieldAlert className="w-6 h-6 text-red-400" /> Security & Best Practices
          </h2>
          <ul className="space-y-3">
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300">Always use a virtual environment (`.venv`) when running python backends to isolate dependencies.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300">Never commit your `.env` files or hardcode API keys. The system uses secure environment variables for all external integrations.</span>
            </li>
          </ul>
        </section>

      </div>
    </div>
  );
}
