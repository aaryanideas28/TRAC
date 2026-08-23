import React from 'react';
import type { BeforeAfterMetrics } from '../types/railway';
import { Sparkles, Zap, CheckCircle2 } from 'lucide-react';

interface BeforeAfterComparisonProps {
  metrics: BeforeAfterMetrics;
}

export const BeforeAfterComparison: React.FC<BeforeAfterComparisonProps> = ({ metrics }) => {
  return (
    <div className="card-container border-2 border-emerald-500/30 bg-slate-900/90 shadow-2xl relative overflow-hidden space-y-4">
      {/* Background Glow Effect */}
      <div className="absolute -top-24 -right-24 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

      {/* Primary Section Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <h2 className="text-base font-extrabold text-slate-100 uppercase tracking-wider flex items-center gap-2">
              Impact of AI Optimization
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono font-bold">
                VALIDATED 10-TRAIN BENCHMARK
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Comparative Analysis: Legacy Baseline vs Infrastructure-Aware OR-Tools CP-SAT Algorithm
            </p>
          </div>
        </div>

        <span className="text-xs px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-emerald-400 font-mono flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Validated Evidence
        </span>
      </div>

      {/* Primary Evidence: Validated 10-Train Benchmark Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* WITHOUT INFRASTRUCTURE-AWARE OPTIMIZATION */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-rose-500/20 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-sm font-bold text-rose-400">WITHOUT INFRASTRUCTURE-AWARE OPTIMIZATION</h3>
            <span className="text-xs font-mono text-slate-500">Legacy Baseline</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-500">Total Completion Delay</span>
              <p className="text-lg font-bold text-rose-400">200.52 min</p>
            </div>

            <div>
              <span className="text-slate-500">Optimizer-Added Hold</span>
              <p className="text-lg font-bold text-rose-400">19.55 min</p>
            </div>

            <div>
              <span className="text-slate-500">Zero-Hold Trains</span>
              <p className="text-lg font-bold text-slate-200">3 trains</p>
            </div>

            <div>
              <span className="text-slate-500">Modeled Headway Violations</span>
              <p className="text-lg font-bold text-emerald-400">0 violations</p>
            </div>
          </div>
        </div>

        {/* INFRASTRUCTURE-AWARE CP-SAT */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-500/40 space-y-3 shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4" />
              INFRASTRUCTURE-AWARE CP-SAT
            </h3>
            <span className="text-xs font-mono text-emerald-400">Optimized</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-500">Total Completion Delay</span>
              <p className="text-lg font-bold text-emerald-400">
                195.82 min
                <span className="text-xs font-normal text-emerald-500 ml-1">(↓ 2.34%)</span>
              </p>
            </div>

            <div>
              <span className="text-slate-500">Optimizer-Added Hold</span>
              <p className="text-lg font-bold text-emerald-400">
                11.65 min
                <span className="text-xs font-normal text-emerald-500 ml-1">(↓ 40.41%)</span>
              </p>
            </div>

            <div>
              <span className="text-slate-500">Zero-Hold Trains</span>
              <p className="text-lg font-bold text-emerald-400">
                3 → 5
                <span className="text-xs font-normal text-emerald-500 ml-1">(+66.7%)</span>
              </p>
            </div>

            <div>
              <span className="text-slate-500">Modeled Headway Violations</span>
              <p className="text-lg font-bold text-emerald-400">
                0
                <span className="text-xs font-normal text-emerald-500 ml-1">(Enforced)</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Evidence: Demonstration Scenario Card */}
      <div className="pt-2 border-t border-slate-800/80">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            DEMONSTRATION SCENARIO METRICS
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
            Scenario-dependent simulation metric
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-slate-950/40 p-3 rounded-lg border border-slate-800/50">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Manual Dispatch Throughput:</span>
            <span className="font-mono text-slate-300 font-bold">{metrics.without_ai.throughput} trains/hr</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">AI Dispatch Throughput:</span>
            <span className="font-mono text-emerald-400 font-bold">{metrics.with_ai.throughput} trains/hr (+{metrics.improvements.throughput_increase_pct}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
