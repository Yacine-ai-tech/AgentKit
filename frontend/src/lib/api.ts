/** Typed client for the AgentKit read-only facade.
 *  Every endpoint executes the SAME function the corresponding MCP tool runs. */

export type ToolParam = { name: string; type: string; required: boolean; default?: unknown };
export type ToolMeta = { 
  name: string; 
  description: string; 
  params: ToolParam[]; 
  endpoint: string;
  effect?: string;
  scopes?: string[];
  pack?: string;
};

export type ToolPolicy = {
  name: string;
  effect: string;
  scopes: string[];
  rate_limit?: number | null;
  requires_approval?: boolean | null;
  description: string;
};

export type PolicyResponse = {
  writes_enabled: boolean;
  approval_configured: boolean;
  granted_scopes: string[];
  tools: Record<string, ToolPolicy>;
  audit_sink: string | null;
};

export type KPI = Record<string, unknown> & {
  metric?: string;
  category?: string;
  period?: string;
  value?: number;
  unit?: string | null;
};

export type HealthScore = {
  score: number;
  interpretation: string;
  components: Record<string, number>;
  error?: string;
};

export type Anomalies = {
  anomalies: (Record<string, unknown> & { metric?: string; period?: string; value?: number; z_score?: number })[];
  total: number;
  threshold: number;
  method?: string;
  error?: string;
};

export type Forecast = {
  metric?: string;
  forecast: { period: string; value: number }[];
  lower_ci: number[];
  upper_ci: number[];
  confidence_level?: number;
  method: string;
  note?: string;
  error?: string;
};

export type Summary = {
  summary: string;
  health_score: number;
  interpretation: string;
  components: Record<string, number>;
  key_metrics: KPI[];
  anomalies: Record<string, unknown>[];
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const BASE = import.meta.env.VITE_API_BASE_URL || "";
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

async function req<T>(path: string, init?: RequestInit, retryCount = 0): Promise<T> {
  try {
    const res = await fetch(BASE + path, init);
    if (!res.ok) {
      if (res.status >= 500 && retryCount < 5) {
        await delay(2000 * (retryCount + 1));
        return req<T>(path, init, retryCount + 1);
      }
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail ?? JSON.stringify(body);
      } catch { /* keep statusText */ }
      throw new ApiError(res.status, detail);
    }
    return res.json() as Promise<T>;
  } catch (err: any) {
    if ((err instanceof TypeError || err.message === 'Failed to fetch') && retryCount < 5) {
      await delay(2000 * (retryCount + 1));
      return req<T>(path, init, retryCount + 1);
    }
    throw err;
  }
}

const q = (params: Record<string, string | number | undefined>) => {
  const s = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");
  return s ? `?${s}` : "";
};

export const api = {
  health: () => req<{ status: string }>("/health"),
  policy: () => req<PolicyResponse>("/api/policy"),
  tools: () => req<{ tools: ToolMeta[]; resources: string[]; prompts: string[] }>("/api/tools"),
  kpis: (p: { domain?: string; period_from?: string; period_to?: string; metric_filter?: string; limit?: number }) =>
    req<{ kpis: KPI[]; total: number; error?: string }>(`/api/kpis${q(p)}`),
  healthScore: (domain?: string) => req<HealthScore>(`/api/health-score${q({ domain })}`),
  anomalies: (domain: string, threshold = 2.5) =>
    req<Anomalies>(`/api/anomalies${q({ domain, threshold })}`),
  forecast: (metric: string, periods = 6) => req<Forecast>(`/api/forecast${q({ metric, periods })}`),
  metrics: (domain?: string) =>
    req<{ metrics: string[]; categories: string[]; periods: string[]; error?: string }>(`/api/metrics${q({ domain })}`),
  summary: () => req<Summary>("/api/summary"),
  observability: (limit = 100) => req<{ requests: ObsRequest[]; capacity: number }>(`/api/observability?limit=${limit}`),
  runWorkflow: (question: string) =>
    req<WorkflowResult>("/api/workflow/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
  /** Generic runner for the Tools try-it page. */
  run: (endpoint: string, params: Record<string, string | number | undefined>) =>
    req<Record<string, unknown>>(`${endpoint}${q(params)}`),
};

export type ObsRequest = { ts: string; method: string; path: string; query: string; status: number; ms: number };
export type WorkflowResult = {
  question: string;
  plan?: string;
  tool_calls?: { tool?: string; args?: unknown; result?: unknown }[];
  report?: string;
  report_sections?: Record<string, string>;
  raw_data?: unknown;
  error?: string;
  _elapsed_ms?: number;
  [k: string]: unknown;
};

export const DOMAINS = ["Finance", "Growth", "Operations", "People", "ESG", "IT_Ops"];

export function isUnavailable(e: unknown): boolean {
  return e instanceof ApiError && e.status === 503;
}
