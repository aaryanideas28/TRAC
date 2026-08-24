import React, { useState } from 'react';
import type { AiRecommendation, ConflictItem } from '../types/railway';
import { Sparkles, ArrowRight, Clock, ShieldCheck, Zap, GitCommit, CornerDownRight, Gauge, Layers, Filter, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface AiRecommendationPanelProps {
  recommendations: AiRecommendation[];
  conflicts?: ConflictItem[];
}

export const AiRecommendationPanel: React.FC<AiRecommendationPanelProps> = ({
  recommendations,
  conflicts = [],
}) => {
  const [activeFilter, setActiveFilter] = useState<string>('ALL');

  const activeConflicts = conflicts.filter((c) => c.status === 'DETECTED');

  const getActionBadge = (type: string) => {
    switch (type) {
      case 'PROCEED':
        return (
          <span className="px-2.5 py-1 rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <Zap className="w-3.5 h-3.5 fill-current" /> PROCEED
          </span>
        );
      case 'HOLD':
        return (
          <span className="px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <Clock className="w-3.5 h-3.5" /> HOLD
          </span>
        );
      case 'TRACK_CHANGE':
        return (
          <span className="px-2.5 py-1 rounded-md bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <GitCommit className="w-3.5 h-3.5" /> TRACK REROUTE
          </span>
        );
      case 'OVERTAKE_LOOP':
        return (
          <span className="px-2.5 py-1 rounded-md bg-purple-500/20 text-purple-400 border border-purple-500/30 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <CornerDownRight className="w-3.5 h-3.5" /> LOOP OVERTAKE
          </span>
        );
      case 'SPEED_ADVISORY':
        return (
          <span className="px-2.5 py-1 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <Gauge className="w-3.5 h-3.5" /> SPEED ADVISORY
          </span>
        );
      case 'PLATFORM_REASSIGN':
        return (
          <span className="px-2.5 py-1 rounded-md bg-blue-500/20 text-blue-400 border border-blue-500/30 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <Layers className="w-3.5 h-3.5" /> PLATFORM REASSIGN
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 text-xs font-bold">
            {type}
          </span>
        );
    }
  };

  const filteredRecs = recommendations.filter((r) => {
    if (activeFilter === 'ALL') return true;
    if (activeFilter === 'OVERTAKE') return r.action_type === 'OVERTAKE_LOOP';
    if (activeFilter === 'REROUTE') return r.action_type === 'TRACK_CHANGE';
    if (activeFilter === 'HOLD') return r.action_type === 'HOLD';
    if (activeFilter === 'PROCEED') return r.action_type === 'PROCEED' || r.action_type === 'SPEED_ADVISORY';
    return true;
  });

  return (
    <div className="w-full p-5 rounded-2xl bg-slate-900/95 border border-slate-800 shadow-2xl space-y-4">
      {/* Header with Title & Conflict Summary */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Sparkles className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-extrabold text-slate-100 flex items-center gap-2">
              AI Operational Traffic Recommendations & Conflict Resolution
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800">
                {recommendations.length} Active Dispatch Decisions
              </span>
            </h2>
            <p className="text-xs text-slate-400">Google OR-Tools CP-SAT Mathematical Dispatch, Headway Sequencing & Precedence Control</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeConflicts.length > 0 ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-bold animate-pulse">
              <AlertTriangle className="w-4 h-4" />
              <span>{activeConflicts.length} Active Conflict Detected</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold">
              <CheckCircle2 className="w-4 h-4" />
              <span>No active conflicts detected • 18 Trains Monitored</span>
            </div>
          )}
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-950 text-slate-300 border border-slate-800 font-mono hidden md:inline-block">
            Engine: CP-SAT + ML
          </span>
        </div>
      </div>

      {/* Active Conflict Banner if Any */}
      {activeConflicts.length > 0 && (
        <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-800/60 space-y-2 text-xs font-mono">
          <div className="flex items-center justify-between text-rose-300 font-bold">
            <span className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              Active Track Section Conflict: {activeConflicts[0].section}
            </span>
            <span className="px-2 py-0.5 rounded bg-rose-900/60 text-rose-200 text-[10px] font-extrabold">
              SEVERITY: {activeConflicts[0].severity}
            </span>
          </div>
          <p className="text-slate-300 font-sans text-xs">
            Trains Involved: <span className="font-bold text-rose-300">{activeConflicts[0].trains_involved.join(' ↔ ')}</span>. Resolution: {activeConflicts[0].ai_resolution}
          </p>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-950 p-1.5 rounded-xl border border-slate-800/80 text-xs">
          <div className="flex items-center gap-1 text-slate-500 px-2 font-semibold">
            <Filter className="w-3 h-3" /> Filter:
          </div>
          <button
            onClick={() => setActiveFilter('ALL')}
            className={`px-2.5 py-1 rounded-lg transition font-medium ${
              activeFilter === 'ALL' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            All ({recommendations.length})
          </button>
          <button
            onClick={() => setActiveFilter('OVERTAKE')}
            className={`px-2.5 py-1 rounded-lg transition font-medium ${
              activeFilter === 'OVERTAKE' ? 'bg-purple-950 text-purple-300 font-bold border border-purple-800/50' : 'text-slate-400 hover:text-purple-300'
            }`}
          >
            Loop Overtakes
          </button>
          <button
            onClick={() => setActiveFilter('REROUTE')}
            className={`px-2.5 py-1 rounded-lg transition font-medium ${
              activeFilter === 'REROUTE' ? 'bg-indigo-950 text-indigo-300 font-bold border border-indigo-800/50' : 'text-slate-400 hover:text-indigo-300'
            }`}
          >
            Track Crossovers
          </button>
          <button
            onClick={() => setActiveFilter('HOLD')}
            className={`px-2.5 py-1 rounded-lg transition font-medium ${
              activeFilter === 'HOLD' ? 'bg-amber-950 text-amber-300 font-bold border border-amber-800/50' : 'text-slate-400 hover:text-amber-300'
            }`}
          >
            Headway Holds
          </button>
          <button
            onClick={() => setActiveFilter('PROCEED')}
            className={`px-2.5 py-1 rounded-lg transition font-medium ${
              activeFilter === 'PROCEED' ? 'bg-emerald-950 text-emerald-300 font-bold border border-emerald-800/50' : 'text-slate-400 hover:text-emerald-300'
            }`}
          >
            Speed & Green Wave
          </button>
        </div>

        <div className="text-xs text-slate-400 font-mono">
          Showing <span className="font-bold text-slate-200">{filteredRecs.length}</span> of {recommendations.length} recommendations
        </div>
      </div>

      {/* Expanded Multi-Column Recommendations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filteredRecs.map((rec) => (
          <div
            key={rec.id}
            className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition shadow-lg flex flex-col justify-between space-y-3"
          >
            <div className="space-y-2.5">
              {/* Header: Action Badge & Train Info */}
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  {getActionBadge(rec.action_type)}
                  <div className="font-bold text-slate-100 text-sm">{rec.affected_train_name}</div>
                </div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 text-cyan-400 border border-slate-800 font-bold shrink-0">
                  {rec.affected_train_id}
                </span>
              </div>

              {/* Recommendation Instruction Action Banner */}
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="font-bold text-slate-100 text-xs">{rec.action}</span>
              </div>

              {/* Resource Target */}
              <div className="text-[11px] text-slate-400 flex items-center justify-between font-mono bg-slate-900/50 px-2.5 py-1.5 rounded-lg">
                <span>Target Resource:</span>
                <span className="text-cyan-300 font-bold truncate max-w-[180px]">{rec.assigned_track}</span>
              </div>

              {/* AI Operational Rationale */}
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 p-2.5 rounded-lg border border-slate-900/80">
                <span className="text-indigo-400 font-bold">Rationale: </span>
                {rec.reason}
              </p>
            </div>

            {/* Metrics & Solvers Footer */}
            <div className="pt-2 text-xs border-t border-slate-800/80 flex items-center justify-between text-slate-400 font-mono">
              <div>
                Delay Saved: <span className="font-bold text-emerald-400">+{rec.expected_delay_reduction_min}m</span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px]">
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-slate-300 font-bold">{rec.solver_status || 'OPTIMAL'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AiRecommendationPanel;
