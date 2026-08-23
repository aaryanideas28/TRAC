import React from 'react';
import type { ConflictItem } from '../types/railway';
import { AlertTriangle, ShieldCheck, Clock, Layers } from 'lucide-react';

interface ConflictMonitorProps {
  conflicts: ConflictItem[];
}

export const ConflictMonitor: React.FC<ConflictMonitorProps> = ({ conflicts }) => {
  return (
    <div className="card-container">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">Live Conflict Radar Monitor</h2>
            <p className="text-xs text-slate-400">Real-Time Detection & Resolution of Signal Conflicts</p>
          </div>
        </div>

        <span className="text-xs px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-300 font-mono">
          Buffer: 120s
        </span>
      </div>

      <div className="space-y-3">
        {conflicts.map((c) => (
          <div
            key={c.id}
            className={`p-3.5 rounded-xl border transition ${
              c.status === 'RESOLVED'
                ? 'bg-emerald-500/5 border-emerald-500/30'
                : 'bg-amber-500/5 border-amber-500/30'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-slate-300">{c.id}</span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                    c.severity === 'HIGH'
                      ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {c.severity} SEVERITY
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                {c.status === 'RESOLVED' ? (
                  <span className="flex items-center gap-1 text-xs font-bold text-emerald-400">
                    <ShieldCheck className="w-3.5 h-3.5" /> Resolved
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs font-bold text-amber-400">
                    <Clock className="w-3.5 h-3.5" /> Predicted in {c.predicted_in_min} min
                  </span>
                )}
              </div>
            </div>

            <div className="text-xs space-y-1">
              <div className="flex items-center justify-between text-slate-300 font-medium">
                <span className="flex items-center gap-1 text-slate-400">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  Section: {c.section}
                </span>
                <span className="font-mono text-slate-300">Trains: {c.trains_involved.join(' ↔ ')}</span>
              </div>

              <p className="text-[11px] text-slate-400 bg-slate-950/60 p-2 rounded border border-slate-900 leading-relaxed">
                <span className="text-emerald-400 font-semibold">AI Resolution Strategy: </span>
                {c.ai_resolution}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
