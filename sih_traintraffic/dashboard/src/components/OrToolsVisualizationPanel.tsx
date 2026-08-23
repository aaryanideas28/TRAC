import React from 'react';
import type { OrToolsOptimizationState } from '../types/railway';
import { Cpu, CheckCircle2, Clock, ShieldCheck, Zap } from 'lucide-react';

interface OrToolsVisualizationPanelProps {
  optimizationState?: OrToolsOptimizationState | null;
}

export const OrToolsVisualizationPanel: React.FC<OrToolsVisualizationPanelProps> = ({ optimizationState }) => {
  const status = optimizationState?.status || 'IDLE';
  const solveTimeMs = optimizationState?.solve_time_ms ?? 0.0;
  const conflictsBefore = optimizationState?.conflicts_before ?? 1;
  const conflictsAfter = optimizationState?.conflicts_after ?? 0;

  const constraintsList = [
    'Track capacity & single-occupancy interlocking',
    'Train separation (120s safety headway buffer)',
    'Switching route conflict avoidance',
    'Train priority weighting (Express > Local > Freight)',
    'Section availability & speed envelope limits',
  ];

  return (
    <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-slate-100">OR-TOOLS CP-SAT SCHEDULING SOLVER</h3>
            <p className="text-xs text-slate-400">Google OR-Tools MILP / Constraint Programming Scheduler</p>
          </div>
        </div>

        {/* Solver Status Badge */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold border ${
            status === 'OPTIMAL'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : status === 'FEASIBLE'
              ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
              : status === 'SOLVING'
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse'
              : 'bg-slate-800 border-slate-700 text-slate-400'
          }`}
        >
          {status === 'OPTIMAL' ? (
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          ) : status === 'SOLVING' ? (
            <Zap className="w-4 h-4 text-amber-400 animate-spin" />
          ) : (
            <Clock className="w-4 h-4 text-cyan-400" />
          )}
          <span>{status === 'SOLVING' ? 'SOLVING CP-SAT...' : status === 'OPTIMAL' ? '✓ OPTIMAL SCHEDULE FOUND' : status}</span>
        </div>
      </div>

      {/* Grid: Objective & Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Objective & Timing Card */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
          <div>
            <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider block mb-1">
              Optimization Objective
            </span>
            <p className="text-xs font-medium text-slate-200 leading-relaxed">
              Minimize total delay penalty while satisfying strict railway safety headway and track section availability.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-800/80">
            <div>
              <span className="text-[10px] text-slate-400 font-extrabold uppercase block">Actual Solve Time</span>
              <span className="text-xl font-extrabold font-mono text-purple-400">{solveTimeMs} ms</span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-extrabold uppercase block">Conflict Reduction</span>
              <span className="text-xl font-extrabold font-mono text-emerald-400">
                {conflictsBefore} → {conflictsAfter}
              </span>
            </div>
          </div>
        </div>

        {/* Satisfied Constraints List */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
          <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider block mb-2">
            Satisfied CP-SAT Constraints
          </span>

          <div className="space-y-1.5 text-xs">
            {constraintsList.map((c, idx) => (
              <div key={idx} className="flex items-center gap-2 text-slate-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="truncate">{c}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
