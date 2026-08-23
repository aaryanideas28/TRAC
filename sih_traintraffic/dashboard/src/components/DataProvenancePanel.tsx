import React from 'react';
import { Database, CheckCircle2, ShieldCheck, Layers, Server, Activity } from 'lucide-react';

export const DataProvenancePanel: React.FC = () => {
  const statusItems = [
    { label: 'RailRadar Telemetry', status: 'REPLAY', type: 'replay', desc: 'Pre-fetched RailRadar observation snapshots replayed offline', icon: Activity },
    { label: 'Random Forest Model', status: 'LOADED', type: 'loaded', desc: 'Scikit-learn Regressor & Classifier delay risk pipeline', icon: CheckCircle2 },
    { label: 'Railway Graph Topology', status: 'LOADED', type: 'loaded', desc: 'Directed network graph from CSMT–Thane infrastructure CSV', icon: Layers },
    { label: 'Infrastructure Model', status: 'LOADED', type: 'loaded', desc: '4-track (CSMT-Sion) and 6-track (Kurla-Thane) corridor resources', icon: Database },
    { label: 'OR-Tools CP-SAT Solver', status: 'READY', type: 'ready', desc: 'Google OR-Tools CP-SAT constraint satisfaction engine', icon: ShieldCheck },
    { label: 'Network Connection', status: 'OFFLINE DEMO', type: 'demo', desc: 'Quota-safe offline simulation mode (0 HTTP sandbox quota used)', icon: Server },
  ];

  return (
    <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">System Data & Model Provenance</h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">Architecture Provenance Status</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {statusItems.map((item, idx) => {
          const IconComp = item.icon;
          return (
            <div
              key={idx}
              className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between space-y-1.5 hover:border-slate-700 transition"
              title={item.desc}
            >
              <div className="flex items-center justify-between text-slate-400">
                <IconComp className="w-3.5 h-3.5 text-slate-400" />
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                    item.type === 'replay'
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                      : item.type === 'loaded'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : item.type === 'ready'
                      ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {item.status}
                </span>
              </div>
              <span className="text-[11px] font-semibold text-slate-200 line-clamp-1">{item.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
