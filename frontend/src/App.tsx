import { Component, ReactNode, lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { BrowserRouter, Route, Routes, Navigate, useLocation } from "react-router-dom";
import { LayoutGrid, Wrench, BarChart3, GitBranch, Cable, Library, Activity, Code2, BookOpen, GraduationCap, Award, Workflow as WorkflowIcon } from "lucide-react";
import { AppShell } from "./kit/AppShell";
import { WakingBackend } from "./kit/misc";
import { Skeleton } from "./kit/primitives";
import { api, login, onAuthRequired, sessionToken } from "./lib/api";
import Overview from "./pages/Overview";

const Tools = lazy(() => import("./pages/Tools"));
const Workflow = lazy(() => import("./pages/Workflow"));
const Connect = lazy(() => import("./pages/Connect"));
const Resources = lazy(() => import("./pages/Resources"));
const Observability = lazy(() => import("./pages/Observability"));
const Intelligence = lazy(() => import("./pages/Intelligence"));
const ArchitecturePage = lazy(() => import("./pages/ArchitecturePage"));
const ResearchPage = lazy(() => import("./pages/ResearchPage"));
const BenchmarkPage = lazy(() => import("./pages/BenchmarkPage"));
const ApiDocs = lazy(() => import("./pages/ApiDocs"));
const LicensePage = lazy(() => import("./pages/LicensePage"));
const UserGuidePage = lazy(() => import("./pages/UserGuidePage"));

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  resetKey?: string;
}

class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null, resetKey: this.props.resetKey };

  static getDerivedStateFromProps(props: { resetKey?: string }, state: ErrorBoundaryState) {
    if (props.resetKey !== state.resetKey) {
      return { hasError: false, error: null, resetKey: props.resetKey };
    }
    return null;
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error("AgentKit UI Error caught by boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center text-red-400 bg-red-950/30 rounded-xl border border-red-800/50 m-4">
          <h2 className="text-xl font-bold mb-2">Component Error</h2>
          <p className="text-sm opacity-80 mb-4">{this.state.error?.message || "An unexpected error occurred."}</p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg text-sm transition"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function RouteErrorBoundary({ children }: { children: ReactNode }) {
  const location = useLocation();
  return <ErrorBoundary resetKey={location.pathname}>{children}</ErrorBoundary>;
}

const NAV = [
  { to: "/", label: "Overview", icon: LayoutGrid },
  { to: "/tools", label: "MCP Tools", icon: Wrench },
  { to: "/intelligence", label: "Business Intelligence", icon: BarChart3 },
  { to: "/workflow", label: "Workflow", icon: GitBranch },
  { to: "/observability", label: "Observability", icon: Activity },
  { to: "/connect", label: "Connect", icon: Cable },
  { to: "/resources", label: "Resources & Prompts", icon: Library },
  { to: "/architecture", label: "Architecture", icon: WorkflowIcon },
  { to: "/research", label: "Research", icon: GraduationCap },
  { to: "/benchmark", label: "Benchmarks", icon: Award },
  { to: "/api-docs", label: "API Docs", icon: Code2 },
  { to: "/user-guide", label: "User Guide", icon: BookOpen }
];

function AuthGate({ children }: { children: ReactNode }) {
  const [needed, setNeeded] = useState(false);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => onAuthRequired(() => setNeeded(true)), []);

  const submit = async () => {
    if (!value.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      await login(value);
      setNeeded(false);
      setValue("");
      window.location.reload();
    } catch {
      setError("Invalid token — check the internal token and try again.");
    } finally {
      setBusy(false);
    }
  };

  if (!needed) return <>{children}</>;

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900/60 p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-100 mb-1">AgentKit access</h2>
        <p className="text-sm text-slate-400 mb-4">
          This deployment requires the internal access token. Enter it once — a short-lived
          session token is kept for this tab only.
        </p>
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Internal token"
          autoFocus
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
        />
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        <button
          onClick={submit}
          disabled={busy || !value.trim()}
          className="mt-4 w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Continue"}
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");
  const [attempts, setAttempts] = useState(0);
  const everConnected = useRef(false);

  const check = useCallback(() => {
    setHealth("checking");
    api.health().then(() => { everConnected.current = true; setHealth("ok"); }).catch(() => setHealth("down"));
  }, []);

  useEffect(() => { check(); }, [check, attempts]);

  useEffect(() => {
    if (health === "down" && attempts < 6) {
      const t = setTimeout(() => setAttempts((a) => a + 1), 8000);
      return () => clearTimeout(t);
    }
  }, [health, attempts]);

  return (
    <BrowserRouter>
      <AppShell product="AgentKit" tagline="AI Agent Intelligence" nav={NAV} health={health}>
        {health === "down" && attempts >= 6 && !everConnected.current ? (
          <WakingBackend waking={attempts < 6} onRetry={() => setAttempts(0)} />
        ) : (
          <Suspense fallback={<Skeleton className="h-64 w-full" />}>
            <RouteErrorBoundary>
              <AuthGate>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/tools" element={<Tools />} />
                <Route path="/intelligence" element={<Intelligence />} />
                <Route path="/workflow" element={<Workflow />} />
                <Route path="/observability" element={<Observability />} />
                <Route path="/connect" element={<Connect />} />
                <Route path="/resources" element={<Resources />} />
                <Route path="/architecture" element={<ArchitecturePage />} />
                <Route path="/research" element={<ResearchPage />} />
                <Route path="/benchmark" element={<BenchmarkPage />} />
                <Route path="/benchmarks" element={<Navigate to="/benchmark" replace />} />
                <Route path="/api-docs" element={<ApiDocs />} />
                              <Route path="/license" element={<LicensePage />} />
<Route path="/user-guide" element={<UserGuidePage />} />
                <Route path="/guide" element={<Navigate to="/user-guide" replace />} />
                <Route path="*" element={<Overview />} />
              </Routes>
              </AuthGate>
            </RouteErrorBoundary>
          </Suspense>
        )}
      </AppShell>
    </BrowserRouter>
  );
}
