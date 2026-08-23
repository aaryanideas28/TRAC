import React from 'react';
import type { SystemEventLogItem } from '../types/railway';
import { Terminal, AlertTriangle, Info, CheckCircle2, Zap } from 'lucide-react';

interface LiveSystemEventLogProps {
  events?: SystemEventLogItem[];
}

export const LiveSystemEventLog: React.FC<LiveSystemEventLogProps> = ({ events = [] }) => {
  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'ERROR':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">ERROR</span>;
      case 'WARNING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">WARN</span>;
      case 'SUCCESS':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">RESOLVED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">INFO</span>;
    }
  };

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'INCIDENT':
        return <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />;
      case 'ML':
        return <Zap className="w-3.5 h-3.5 text-indigo-400 shrink-0" />;
      case 'OPTIMIZATION':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
      default:
        return <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />;
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-3">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-slate-800 text-cyan-400 border border-slate-700">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-slate-100">LIVE SYSTEM EVENT LOG</h3>
            <p className="text-xs text-slate-400">Real-Time Telemetry, Conflict Detection & Solver Dispatches</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          <span>Streaming ({events.length} Events)</span>
        </div>
      </div>

      {/* Terminal Log Output List */}
      <div className="bg-slate-950 rounded-xl border border-slate-800/80 p-3 font-mono text-xs max-h-64 overflow-y-auto space-y-2 divide-y divide-slate-900">
        {events.length === 0 ? (
          <div className="py-6 text-center text-slate-500">No events logged yet. Simulation running...</div>
        ) : (
          events.map((evt) => (
            <div key={evt.id} className="pt-2 first:pt-0 flex items-start justify-between gap-3 text-slate-300">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-slate-500 font-bold text-[11px] shrink-0">{evt.timestamp}</span>
                {getCategoryIcon(evt.category)}
                <span className="truncate">{evt.message}</span>
              </div>
              <div className="shrink-0">{getSeverityBadge(evt.severity)}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
