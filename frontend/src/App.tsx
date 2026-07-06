import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { LayoutGrid, Wrench, BarChart3, GitBranch, Cable, Library } from "lucide-react";
import { AppShell } from "./kit/AppShell";
import { WakingBackend } from "./kit/misc";
import { Skeleton } from "./kit/primitives";
import { api } from "./lib/api";
import Overview from "./pages/Overview";
import Tools from "./pages/Tools";
import Workflow from "./pages/Workflow";
import Connect from "./pages/Connect";
import Resources from "./pages/Resources";

const Intelligence = lazy(() => import("./pages/Intelligence"));

const NAV = [
  { to: "/", label: "Overview", icon: LayoutGrid },
  { to: "/tools", label: "MCP Tools", icon: Wrench },
  { to: "/intelligence", label: "Business Intelligence", icon: BarChart3 },
  { to: "/workflow", label: "Workflow", icon: GitBranch },
  { to: "/connect", label: "Connect", icon: Cable },
  { to: "/resources", label: "Resources & Prompts", icon: Library },
];

export default function App() {
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");
  const [attempts, setAttempts] = useState(0);

  const check = useCallback(() => {
    setHealth("checking");
    api.health().then(() => setHealth("ok")).catch(() => setHealth("down"));
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
        {health !== "ok" && !(health === "checking" && attempts === 0) ? (
          <WakingBackend waking={attempts < 6} onRetry={() => setAttempts(0)} />
        ) : (
          <Suspense fallback={<Skeleton className="h-64 w-full" />}>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/tools" element={<Tools />} />
              <Route path="/intelligence" element={<Intelligence />} />
              <Route path="/workflow" element={<Workflow />} />
              <Route path="/connect" element={<Connect />} />
              <Route path="/resources" element={<Resources />} />
              <Route path="*" element={<Overview />} />
            </Routes>
          </Suspense>
        )}
      </AppShell>
    </BrowserRouter>
  );
}
