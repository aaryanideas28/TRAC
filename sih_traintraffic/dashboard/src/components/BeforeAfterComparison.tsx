import React from 'react';
import type { BeforeAfterMetrics } from '../types/railway';
import { Sparkles, Zap } from 'lucide-react';

interface BeforeAfterComparisonProps {
  metrics: BeforeAfterMetrics;
}

export const BeforeAfterComparison: React.FC<BeforeAfterComparisonProps> = ({ metrics }) => {
  return (
    <div className="card-container border-2 border-emerald-500/30 bg-slate-900/90 shadow-2xl relative overflow-hidden">
      {/* Background Glow Effect */}
      <div className="absolute -top-24 -right-24 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <h2 className="text-base font-extrabold text-slate-100 uppercase tracking-wider flex items-center gap-2">
              Impact of AI Optimization
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono font-bold">
                BEFORE vs WITH AI
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Comparative Analysis: Traditional Manual Dispatch vs Nexora OR-Tools CP-SAT Algorithm
            </p>
          </div>
        </div>

        <span className="text-xs px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-slate-300 font-mono">
          Engine: OR-Tools CP-SAT
        </span>
      </div>

      {/* Side-by-Side Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* WITHOUT AI */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-rose-500/20 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-sm font-bold text-rose-400">WITHOUT AI (Manual Dispatch)</h3>
            <span className="text-xs font-mono text-slate-500">Baseline</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-500">Throughput</span>
              <p className="text-lg font-bold text-slate-200">{metrics.without_ai.throughput} trains/hr</p>
            </div>

            <div>
              <span className="text-slate-500">Average Delay</span>
              <p className="text-lg font-bold text-rose-400">{metrics.without_ai.average_delay} min</p>
            </div>

            <div>
              <span className="text-slate-500">Track Utilization</span>
              <p className="text-lg font-bold text-slate-200">{metrics.without_ai.track_utilization}%</p>
            </div>

            <div>
              <span className="text-slate-500">Station Waiting Time</span>
              <p className="text-lg font-bold text-rose-400">{metrics.without_ai.waiting_time} min</p>
            </div>
          </div>
        </div>

        {/* WITH AI */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-500/40 space-y-3 shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4" />
              WITH AI (OR-Tools CP-SAT)
            </h3>
            <span className="text-xs font-mono text-emerald-400">Optimized</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-500">Throughput</span>
              <p className="text-lg font-bold text-emerald-400">
                {metrics.with_ai.throughput} trains/hr
                <span className="text-xs font-normal text-emerald-500 ml-1">(+{metrics.improvements.throughput_increase_pct}%)</span>
              </p>
            </div>

            <div>
              <span className="text-slate-500">Average Delay</span>
              <p className="text-lg font-bold text-emerald-400">
                {metrics.with_ai.average_delay} min
                <span className="text-xs font-normal text-emerald-500 ml-1">(-{metrics.improvements.delay_reduction_pct}%)</span>
              </p>
            </div>

            <div>
              <span className="text-slate-500">Track Utilization</span>
              <p className="text-lg font-bold text-emerald-400">
                {metrics.with_ai.track_utilization}%
                <span className="text-xs font-normal text-emerald-500 ml-1">(+{metrics.improvements.utilization_increase_pct}%)</span>
              </p>
            </div>

            <div>
              <span className="text-slate-500">Station Waiting Time</span>
              <p className="text-lg font-bold text-emerald-400">
                {metrics.with_ai.waiting_time} min
                <span className="text-xs font-normal text-emerald-500 ml-1">(-{metrics.improvements.waiting_time_reduction_pct}%)</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
