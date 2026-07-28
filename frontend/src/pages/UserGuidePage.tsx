import React from 'react';
import { BookOpen, Monitor, Terminal, FileCode, CheckCircle, ShieldAlert, Database, 
         Brains, Settings, Globe, Zap, Server, Users, ChartBar, AlertTriangle, Lightbulb } from 'lucide-react';

export default function UserGuidePage() {
  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-8">
        <BookOpen className="w-10 h-10 text-blue-500" />
        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
          AgentKit - Complete User Guide
        </h1>
      </div>

      <p className="text-lg text-gray-300 mb-8 leading-relaxed">
        AgentKit is a Model Context Protocol (MCP) server that provides business intelligence tools for AI agents. 
        It enables agents to access real KPI data, perform forecasting, detect anomalies, and generate executive summaries 
        - making it perfect for business analytics, reporting, and decision-making workflows.
      </p>

      <div className="space-y-8 text-gray-200">
        
        {/* What is AgentKit */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Brains className="w-6 h-6 text-purple-400" /> What is AgentKit?
          </h2>
          <div className="space-y-4">
            <p className="text-gray-300">
              AgentKit is a production-grade MCP server that provides <strong className="text-blue-400">6 powerful business intelligence tools</strong>:
            </p>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 className="font-semibold text-green-400 text-lg mb-2">📊 query_kpis</h3>
                <p className="text-sm text-gray-300">Query business KPIs by domain, time period, and metrics. Supports finance, people, operations, ESG data.</p>
              </div>
              <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 className="font-semibold text-blue-400 text-lg mb-2">🏥 get_company_health</h3>
                <p className="text-sm text-gray-300">Get composite health scores across business domains with trend analysis.</p>
              </div>
              <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 className="font-semibold text-red-400 text-lg mb-2">⚠️ detect_kpi_anomalies</h3>
                <p className="text-sm text-gray-300">Find outliers and anomalies in KPI data using statistical methods (z-score, IQR).</p>
              </div>
              <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 className="font-semibold text-purple-400 text-lg mb-2">📈 forecast_metric</h3>
                <p className="text-sm text-gray-300">Generate time-series forecasts with confidence intervals for any metric.</p>
              </div>
              <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 className="font-semibold text-yellow-400 text-lg mb-2">🔍 list_available_metrics</h3>
                <p className="text-sm text-gray-300">Discover available metrics, categories, and time periods in the database.</p>
              </div>
              <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 className="font-semibold text-cyan-400 text-lg mb-2">📋 get_executive_summary</h3>
                <p className="text-sm text-gray-300">Generate comprehensive executive summaries with health, KPIs, and anomalies.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Universal Agent Integration */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Globe className="w-6 h-6 text-blue-400" /> Universal Agent Integration
          </h2>
          <p className="text-gray-300 mb-6">
            AgentKit works with <strong className="text-green-400">any MCP-compatible agent</strong> including Claude Desktop, Cursor, Windsurf, and custom implementations.
          </p>
          
          <div className="space-y-6">
            {/* Claude Desktop */}
            <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-lg text-gray-100 flex items-center gap-2 mb-3">
                <FileCode className="w-5 h-5 text-orange-400" /> Claude Desktop Integration
              </h3>
              <p className="text-sm text-gray-300 mb-3">Add to your <code className="bg-gray-800 px-2 py-1 rounded">claude_desktop_config.json</code>:</p>
              <pre className="bg-gray-950 p-4 rounded-lg text-sm font-mono text-green-300 overflow-x-auto">
{`{
  "mcpServers": {
    "agentkit": {
      "command": "python",
      "args": ["-m", "agentkit_mcp.mcp_server"],
      "env": {
        "POSTGRES_URL": "postgresql://user:pass@host/db",
        "GROQ_API_KEY": "your_groq_key",
        "ANTHROPIC_API_KEY": "your_anthropic_key"
      }
    }
  }
}`}
              </pre>
            </div>

            {/* Cursor */}
            <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-lg text-gray-100 flex items-center gap-2 mb-3">
                <Terminal className="w-5 h-5 text-blue-400" /> Cursor IDE Integration
              </h3>
              <p className="text-sm text-gray-300 mb-3">Cursor Settings → Features → MCP Servers → Add New:</p>
              <ul className="list-disc list-inside text-sm text-gray-300 space-y-2 ml-2">
                <li><strong>Type:</strong> Command</li>
                <li><strong>Name:</strong> agentkit</li>
                <li><strong>Command:</strong> <code className="bg-gray-800 px-2 py-1 rounded">python -m agentkit_mcp.mcp_server</code></li>
                <li><strong>Environment:</strong> Set POSTGRES_URL and API keys</li>
              </ul>
            </div>

            {/* Remote SSE */}
            <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-lg text-gray-100 flex items-center gap-2 mb-3">
                <Server className="w-5 h-5 text-purple-400" /> Remote SSE (Hosted)
              </h3>
              <p className="text-sm text-gray-300 mb-3">Connect to hosted AgentKit without local setup:</p>
              <pre className="bg-gray-950 p-4 rounded-lg text-sm font-mono text-green-300 overflow-x-auto">
{`{
  "mcpServers": {
    "agentkit-remote": {
      "transport": "sse",
      "url": "https://your-agentkit-url.com/sse",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_AUTH_TOKEN"
      }
    }
  }
}`}
              </pre>
            </div>
          </div>
        </section>

        {/* Configuration & Requirements */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Settings className="w-6 h-6 text-amber-400" /> Configuration & Requirements
          </h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-blue-400 text-lg mb-2 flex items-center gap-2">
                <Database className="w-5 h-5" /> Database Setup
              </h3>
              <ul className="text-sm text-gray-300 space-y-2">
                <li>• PostgreSQL database (Neon recommended)</li>
                <li>• Create <code className="bg-gray-800 px-1 rounded">kpi_metrics</code> table</li>
                <li>• Seed with business data using <code className="bg-gray-800 px-1 rounded">python -m src.data.seed</code></li>
                <li>• Set <code className="bg-gray-800 px-1 rounded">POSTGRES_URL</code> environment variable</li>
              </ul>
            </div>

            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-green-400 text-lg mb-2 flex items-center gap-2">
                <Zap className="w-5 h-5" /> API Keys Required
              </h3>
              <ul className="text-sm text-gray-300 space-y-2">
                <li>• <strong>GROQ_API_KEY:</strong> Default LLM provider</li>
                <li>• <strong>ANTHROPIC_API_KEY:</strong> Reasoning LLM</li>
                <li>• <strong>OPENAI_API_KEY:</strong> Optional backup</li>
                <li>• <strong>MCP_AUTH_TOKEN:</strong> For remote SSE access</li>
              </ul>
            </div>

            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-purple-400 text-lg mb-2 flex items-center gap-2">
                <Monitor className="w-5 h-5" /> Installation
              </h3>
              <pre className="bg-gray-950 p-3 rounded-lg text-xs font-mono text-green-300 overflow-x-auto">
{`git clone https://github.com/Yacine-ai-tech/AgentKit
cd AgentKit
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt`}
              </pre>
            </div>

            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-red-400 text-lg mb-2 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" /> Data Scenarios
              </h3>
              <p className="text-sm text-gray-300 mb-2">Use Admin panel to switch between business scenarios:</p>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• <strong>Healthy:</strong> Normal business growth</li>
                <li>• <strong>Declining Revenue:</strong> Financial stress testing</li>
                <li>• <strong>High Churn:</strong> Employee retention crisis</li>
                <li>• <strong>Anomaly Spike:</strong> Outlier detection testing</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Real-World Use Cases */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <Lightbulb className="w-6 h-6 text-yellow-400" /> Real-World Use Cases
          </h2>
          
          <div className="space-y-4">
            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-blue-400 text-lg mb-2">🏢 Executive Reporting</h3>
              <p className="text-sm text-gray-300">
                "Generate monthly executive summary with key financial metrics, health scores, and any anomalies requiring attention."
              </p>
              <p className="text-xs text-gray-500 mt-2">Tools: get_executive_summary, query_kpis, get_company_health</p>
            </div>

            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-green-400 text-lg mb-2">📈 Financial Forecasting</h3>
              <p className="text-sm text-gray-300">
                "Forecast revenue for the next 6 months with 95% confidence intervals and identify any concerning trends."
              </p>
              <p className="text-xs text-gray-500 mt-2">Tools: forecast_metric, query_kpis, detect_kpi_anomalies</p>
            </div>

            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-purple-400 text-lg mb-2">👥 HR Analytics</h3>
              <p className="text-sm text-gray-300">
                "Analyze headcount trends, employee turnover rates, and identify any unusual patterns in people metrics."
              </p>
              <p className="text-xs text-gray-500 mt-2">Tools: query_kpis, detect_kpi_anomalies, get_company_health</p>
            </div>

            <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
              <h3 className="font-semibold text-red-400 text-lg mb-2">⚠️ Anomaly Detection</h3>
              <p className="text-sm text-gray-300">
                "Review all business domains for outliers and anomalies that might indicate problems or opportunities."
              </p>
              <p className="text-xs text-gray-500 mt-2">Tools: detect_kpi_anomalies, list_available_metrics, query_kpis</p>
            </div>
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
              <span className="text-sm text-gray-300"><strong>Use virtual environments:</strong> Always run AgentKit in a .venv to isolate dependencies.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300"><strong>Secure your API keys:</strong> Never commit .env files. Use environment variables for all secrets.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300"><strong>Database security:</strong> Use separate databases for different environments (dev/staging/prod).</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300"><strong>Rate limiting:</strong> Implement rate limiting on the hosted SSE endpoint to prevent abuse.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-sm text-gray-300"><strong>Authentication:</strong> Use MCP_AUTH_TOKEN for remote SSE connections to prevent unauthorized access.</span>
            </li>
          </ul>
        </section>

        {/* API Reference */}
        <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
            <FileCode className="w-6 h-6 text-cyan-400" /> REST API Reference
          </h2>
          <p className="text-gray-300 mb-4">
            AgentKit also provides a REST API for direct integration without MCP:
          </p>
          <div className="space-y-2">
            <div className="bg-gray-900 p-3 rounded-lg border border-gray-700 flex items-center gap-3">
              <span className="bg-green-600 text-xs px-2 py-1 rounded font-mono">GET</span>
              <code className="text-sm text-gray-300">/api/kpis</code>
              <span className="text-xs text-gray-500 ml-auto">Query KPI metrics</span>
            </div>
            <div className="bg-gray-900 p-3 rounded-lg border border-gray-700 flex items-center gap-3">
              <span className="bg-green-600 text-xs px-2 py-1 rounded font-mono">GET</span>
              <code className="text-sm text-gray-300">/api/health-score</code>
              <span className="text-xs text-gray-500 ml-auto">Get company health</span>
            </div>
            <div className="bg-gray-900 p-3 rounded-lg border border-gray-700 flex items-center gap-3">
              <span className="bg-green-600 text-xs px-2 py-1 rounded font-mono">GET</span>
              <code className="text-sm text-gray-300">/api/anomalies</code>
              <span className="text-xs text-gray-500 ml-auto">Detect anomalies</span>
            </div>
            <div className="bg-gray-900 p-3 rounded-lg border border-gray-700 flex items-center gap-3">
              <span className="bg-green-600 text-xs px-2 py-1 rounded font-mono">GET</span>
              <code className="text-sm text-gray-300">/api/forecast</code>
              <span className="text-xs text-gray-500 ml-auto">Generate forecasts</span>
            </div>
            <div className="bg-gray-900 p-3 rounded-lg border border-gray-700 flex items-center gap-3">
              <span className="bg-green-600 text-xs px-2 py-1 rounded font-mono">GET</span>
              <code className="text-sm text-gray-300">/api/scenario</code>
              <span className="text-xs text-gray-500 ml-auto">Get current scenario</span>
            </div>
            <div className="bg-gray-900 p-3 rounded-lg border border-gray-700 flex items-center gap-3">
              <span className="bg-blue-600 text-xs px-2 py-1 rounded font-mono">POST</span>
              <code className="text-sm text-gray-300">/api/scenario</code>
              <span className="text-xs text-gray-500 ml-auto">Switch data scenario</span>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}