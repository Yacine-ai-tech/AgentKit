import { motion } from "framer-motion";
import { ListChecks, Wrench, FileText, Database } from "lucide-react";

export function AgentGraph() {
  return (
    <div className="relative flex items-center justify-between overflow-hidden rounded-xl border border-line bg-surface-2 p-8">
      {/* Background SVG paths */}
      <svg className="absolute inset-0 h-full w-full" style={{ zIndex: 0 }}>
        <path d="M 60 40 Q 200 40 300 80 T 540 80" fill="none" stroke="var(--border-strong)" strokeWidth="2" strokeDasharray="4 4" />
        <path d="M 300 80 Q 400 120 540 80" fill="none" stroke="var(--border-strong)" strokeWidth="2" strokeDasharray="4 4" />
        <motion.path 
          d="M 60 40 Q 200 40 300 80 T 540 80" 
          fill="none" stroke="var(--accent)" strokeWidth="2"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 2, ease: "linear", repeat: Infinity }}
        />
      </svg>
      
      {/* Nodes */}
      <div className="relative z-10 flex flex-col items-center gap-2">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface border border-[var(--accent)] text-[var(--accent)] shadow-[0_0_15px_rgba(34,227,214,0.3)]">
          <ListChecks size={20} />
        </div>
        <div className="text-xs font-semibold">Planner</div>
      </div>
      
      <div className="relative z-10 flex flex-col items-center gap-2 mt-16">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface border border-[var(--accent)] text-[var(--accent)] shadow-[0_0_15px_rgba(34,227,214,0.3)]">
          <Wrench size={20} />
        </div>
        <div className="text-xs font-semibold">Analyst</div>
        <div className="absolute -bottom-8 whitespace-nowrap text-[10px] text-muted"><Database size={10} className="inline mr-1"/>Live Postgres</div>
      </div>
      
      <div className="relative z-10 flex flex-col items-center gap-2">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface border border-[var(--accent)] text-[var(--accent)] shadow-[0_0_15px_rgba(34,227,214,0.3)]">
          <FileText size={20} />
        </div>
        <div className="text-xs font-semibold">Reporter</div>
      </div>
    </div>
  );
}
