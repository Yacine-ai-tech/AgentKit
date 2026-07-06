/** Typed client for the AgentKit read-only facade (GAP_REPORT.md §2).
 *  Every endpoint executes the SAME function the corresponding MCP tool runs. */

export type ToolParam = { name: string; type: string; required: boolean; default?: unknown };
export type ToolMeta = { name: string; description: string; params: ToolParam[]; endpoint: string };

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

async function req<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
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
  /** Generic runner for the Tools try-it page. */
  run: (endpoint: string, params: Record<string, string | number | undefined>) =>
    req<Record<string, unknown>>(`${endpoint}${q(params)}`),
};

export const DOMAINS = ["Finance", "Growth", "Operations", "People", "ESG", "IT_Ops"];

export function isUnavailable(e: unknown): boolean {
  return e instanceof ApiError && e.status === 503;
}
