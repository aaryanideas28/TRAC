import React from 'react';
import { Database, CheckCircle2, Cpu, Layers } from 'lucide-react';

export const DataProvenanceBadge: React.FC = () => {
  return (
    <div className="p-5 rounded-2xl bg-slate-900/95 border border-slate-800 shadow-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-slate-100 flex items-center gap-2">
              DATA PROVENANCE & ARCHITECTURE
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
                100% Real Operational Data
              </span>
            </h3>
            <p className="text-xs text-slate-400">Authentic Mumbai Suburban Rail Feeds vs Competitor Synthetic Datasets</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
            Topology: <span className="text-cyan-400 font-bold">Mumbai Central Line (19 Stns)</span>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
            Solver: <span className="text-emerald-400 font-bold">Google OR-Tools CP-SAT</span>
          </span>
        </div>
      </div>

      {/* Grid Comparison: Our System vs Competitor Systems */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 text-xs font-mono">
        {/* Card 1: Authentic Infrastructure */}
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2">
          <div className="flex items-center gap-2 text-emerald-400 font-bold">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Actual Railway Infrastructure</span>
          </div>
          <p className="text-slate-300 leading-relaxed font-sans text-xs">
            Built on verified Central Railway engineering surveys: 4-track physical corridor from CSMT to Sion (11.9 km) and 6-track corridor from Kurla to Thane (14.7–32.7 km) with verified platform allocations and speed limits.
          </p>
          <div className="text-[10.5px] text-slate-400 pt-1 border-t border-slate-900">
            Source: <code className="text-slate-200">csmt_thane_railway_infrastructure.csv</code>
          </div>
        </div>

        {/* Card 2: Live RailRadar API Data */}
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2">
          <div className="flex items-center gap-2 text-cyan-400 font-bold">
            <Layers className="w-4 h-4 shrink-0" />
            <span>Authentic Train Timetables</span>
          </div>
          <p className="text-slate-300 leading-relaxed font-sans text-xs">
            359 real Central Line trains captured via Indian Railways RailRadar API feeds, including exact service numbers (e.g. 96301 Ambernath Slow, 95011 Khopoli Fast, 22229 Vande Bharat Express) and historical headway intervals.
          </p>
          <div className="text-[10.5px] text-slate-400 pt-1 border-t border-slate-900">
            Dataset: <code className="text-slate-200">20260821T145115Z-3d27e36c_between.json</code>
          </div>
        </div>

        {/* Card 3: Mathematical CP-SAT Optimizer */}
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2">
          <div className="flex items-center gap-2 text-indigo-400 font-bold">
            <Cpu className="w-4 h-4 shrink-0" />
            <span>CP-SAT Physical Validity</span>
          </div>
          <p className="text-slate-300 leading-relaxed font-sans text-xs">
            Strict single-track FIFO headway constraints and designated loop passing logic eliminate physically impossible same-track overtaking, producing mathematically guaranteed optimal dispatches within 150ms.
          </p>
          <div className="text-[10.5px] text-slate-400 pt-1 border-t border-slate-900">
            Algorithm: <code className="text-slate-200">OR-Tools CP-SAT (Levels 1–4)</code>
          </div>
        </div>
      </div>
    </div>
  );
};
