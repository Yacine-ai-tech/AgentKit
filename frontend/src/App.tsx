import UserGuidePage from './pages/UserGuidePage';
import BenchmarkPage from './pages/BenchmarkPage';
import ApiDocs from './pages/ApiDocs';
import { Component, ReactNode, lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { LayoutGrid, Wrench, BarChart3, GitBranch, Cable, Library, Activity, Code2, BookOpen } from "lucide-react";
import { AppShell } from "./kit/AppShell";
import { WakingBackend } from "./kit/misc";
import { Skeleton } from "./kit/primitives";
import { api } from "./lib/api";
import Overview from "./pages/Overview";
import Tools from "./pages/Tools";
import Workflow from "./pages/Workflow";
import Connect from "./pages/Connect";
import Resources from "./pages/Resources";
import Observability from "./pages/Observability";

const Intelligence = lazy(() => import("./pages/Intelligence"));

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
  { to: "/api-docs", label: "API Docs", icon: Code2 },
  { to: "/user-guide", label: "User Guide", icon: BookOpen }
];

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
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/tools" element={<Tools />} />
                <Route path="/intelligence" element={<Intelligence />} />
                <Route path="/workflow" element={<Workflow />} />
                <Route path="/observability" element={<Observability />} />
                <Route path="/connect" element={<Connect />} />
                <Route path="/resources" element={<Resources />} />
                <Route path="/api-docs" element={<ApiDocs />} />
                <Route path="/benchmark" element={<BenchmarkPage />} />
                <Route path="/user-guide" element={<UserGuidePage />} />
                <Route path="*" element={<Overview />} />
              </Routes>
            </RouteErrorBoundary>
          </Suspense>
        )}
      </AppShell>
    </BrowserRouter>
  );
}
