import React from 'react';
import type { BeforeAfterMetrics } from '../types/railway';
import { Sparkles, Zap, CheckCircle2 } from 'lucide-react';

interface BeforeAfterComparisonProps {
  metrics: BeforeAfterMetrics;
}

export const BeforeAfterComparison: React.FC<BeforeAfterComparisonProps> = ({ metrics }) => {
  const before = metrics.without_ai;
  const after = metrics.with_ai;
  const imp = metrics.improvements;

  return (
    <div className="p-5 rounded-2xl border border-emerald-500/30 bg-slate-900/95 shadow-2xl relative overflow-hidden space-y-4">
      {/* Background Glow */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-3 gap-2">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <h2 className="text-base font-extrabold text-slate-100 flex items-center gap-2">
              BEFORE VS AFTER OPTIMIZATION
              <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono font-bold">
                LIVE SIMULATION IMPACT
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Measurable improvement captured live before disruption vs post OR-Tools CP-SAT dispatch
            </p>
          </div>
        </div>

        <span className="text-xs px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-emerald-400 font-mono flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5" />
          {imp.conflict_elimination_pct}% Conflict Elimination
        </span>
      </div>

      {/* Comparative Metric Table */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* BEFORE OPTIMIZATION CARD */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-rose-500/30 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-xs font-extrabold text-rose-400 uppercase tracking-wider">BEFORE OPTIMIZATION</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-300">Unoptimized Incident State</span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Throughput</span>
              <span className="text-sm font-bold text-rose-400">{before.throughput} trains/hr</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Average Delay</span>
              <span className="text-sm font-bold text-rose-400">{before.average_delay} min</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Track Utilization</span>
              <span className="text-sm font-bold text-slate-300">{before.track_utilization}%</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Waiting Time</span>
              <span className="text-sm font-bold text-rose-400">{before.waiting_time} min</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Active Conflicts</span>
              <span className="text-sm font-bold text-rose-400">{before.conflicts} conflicts</span>
            </div>
          </div>
        </div>

        {/* AFTER OPTIMIZATION CARD */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-500/40 space-y-3 shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-xs font-extrabold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              AFTER CP-SAT OPTIMIZATION
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300">CP-SAT Dispatched</span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Throughput</span>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-emerald-400">{after.throughput} trains/hr</span>
                <span className="text-[10px] text-emerald-500 font-normal">(↑ {imp.throughput_increase_pct}%)</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Average Delay</span>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-emerald-400">{after.average_delay} min</span>
                <span className="text-[10px] text-emerald-500 font-normal">(↓ {imp.delay_reduction_pct}%)</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Track Utilization</span>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-emerald-400">{after.track_utilization}%</span>
                <span className="text-[10px] text-emerald-500 font-normal">(↑ {imp.utilization_increase_pct}%)</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Waiting Time</span>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-emerald-400">{after.waiting_time} min</span>
                <span className="text-[10px] text-emerald-500 font-normal">(↓ {imp.waiting_time_reduction_pct}%)</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Active Conflicts</span>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-emerald-400">{after.conflicts} conflicts</span>
                <span className="text-[10px] text-emerald-500 font-normal">(Clean)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
