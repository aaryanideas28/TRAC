import React, { useState } from 'react';
import type { AiRecommendation } from '../types/railway';
import { Sparkles, ArrowRight, Clock, ShieldCheck, Zap, GitCommit, CornerDownRight, Gauge, Layers, Filter } from 'lucide-react';

interface AiRecommendationPanelProps {
  recommendations: AiRecommendation[];
}

export const AiRecommendationPanel: React.FC<AiRecommendationPanelProps> = ({ recommendations }) => {
  const [activeFilter, setActiveFilter] = useState<string>('ALL');

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
    <div className="p-5 rounded-2xl bg-slate-900/95 border border-slate-800 shadow-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Sparkles className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-extrabold text-slate-100 flex items-center gap-2">
              AI Operational Traffic Recommendations
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800">
                {recommendations.length} Active Dispatch Decisions
              </span>
            </h2>
            <p className="text-xs text-slate-400">OR-Tools CP-SAT Conflict-Free Mathematical Dispatch & Headway Sequencing</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-950 text-slate-300 border border-slate-800 font-mono">
            Engine: OR-Tools CP-SAT + ML Classifier
          </span>
        </div>
      </div>

      {/* Filter Tabs */}
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

      {/* Recommendations Cards List */}
      <div className="space-y-3.5 max-h-[560px] overflow-y-auto pr-1">
        {filteredRecs.map((rec) => (
          <div
            key={rec.id}
            className="p-4 rounded-xl bg-slate-900 border border-slate-800/90 hover:border-slate-700 transition shadow-lg space-y-3"
          >
            {/* Header: Action Badge & Train Info */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {getActionBadge(rec.action_type)}
                <span className="font-bold text-slate-100 text-sm">{rec.affected_train_name}</span>
                <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-slate-950 text-cyan-400 border border-slate-800 font-bold">
                  {rec.affected_train_id}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[11px] text-slate-400 block">Assigned Resource</span>
                <span className="text-xs font-semibold text-cyan-300">{rec.assigned_track}</span>
              </div>
            </div>

            {/* Recommendation Instruction Action Banner */}
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0" />
              <span className="font-bold text-slate-100 text-xs sm:text-sm">{rec.action}</span>
            </div>

            {/* AI Operational Rationale */}
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/70 p-3 rounded-lg border border-slate-900">
              <span className="text-indigo-400 font-bold">AI Rationale: </span>
              "{rec.reason}"
            </p>

            {/* Metrics & Solvers Footer */}
            <div className="flex flex-wrap items-center justify-between pt-2 text-xs border-t border-slate-800/60 gap-2">
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-slate-500">Wait Duration: </span>
                  <span className="font-mono font-bold text-slate-200">{rec.waiting_time_sec}s</span>
                </div>
                <div>
                  <span className="text-slate-500">Delay Saved: </span>
                  <span className="font-mono font-bold text-emerald-400">-{rec.expected_delay_reduction_min} min</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {rec.solver_status && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800/70 font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3 text-emerald-400" /> CP-SAT: {rec.solver_status}
                  </span>
                )}
                {rec.ml_congestion_prob !== undefined && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800/70 font-semibold">
                    ML Risk: {Math.round(rec.ml_congestion_prob * 100)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AiRecommendationPanel;
