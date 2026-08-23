import React from 'react';
import type { AiRecommendation } from '../types/railway';
import { Sparkles, ArrowRight, Clock, ShieldCheck, Zap, GitCommit } from 'lucide-react';

interface AiRecommendationPanelProps {
  recommendations: AiRecommendation[];
}

export const AiRecommendationPanel: React.FC<AiRecommendationPanelProps> = ({ recommendations }) => {
  const getActionBadge = (type: string) => {
    switch (type) {
      case 'PROCEED':
        return (
          <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center gap-1">
            <Zap className="w-3 h-3 fill-current" /> PROCEED
          </span>
        );
      case 'HOLD':
        return (
          <span className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-bold flex items-center gap-1">
            <Clock className="w-3 h-3" /> HOLD
          </span>
        );
      case 'TRACK_CHANGE':
        return (
          <span className="px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-xs font-bold flex items-center gap-1">
            <GitCommit className="w-3 h-3" /> TRACK CHANGE
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="card-container">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Sparkles className="w-5 h-5 animate-spin-slow" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">AI Traffic Recommendation</h2>
            <p className="text-xs text-slate-400">OR-Tools CP-SAT Conflict-Free Dispatch Sequence</p>
          </div>
        </div>

        <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
          Engine: OR-Tools CP-SAT
        </span>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition-colors shadow-lg space-y-3"
          >
            {/* Header: Action & Train */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getActionBadge(rec.action_type)}
                <span className="font-bold text-slate-200 text-sm">{rec.affected_train_name}</span>
                <span className="text-xs font-mono text-slate-400">({rec.affected_train_id})</span>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-400 block">Assigned Track</span>
                <span className="text-xs font-medium text-cyan-300">{rec.assigned_track}</span>
              </div>
            </div>

            {/* Recommendation Instruction banner */}
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/50">
              <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0" />
              <span className="font-bold text-slate-100 text-sm">{rec.action}</span>
            </div>

            {/* Reason text */}
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-2.5 rounded-lg border border-slate-900">
              <span className="text-indigo-400 font-semibold">AI Rationale: </span>
              "{rec.reason}"
            </p>

            {/* Metrics Footer */}
            <div className="flex items-center justify-between pt-1 text-xs border-t border-slate-800/60">
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-slate-500">Wait Time: </span>
                  <span className="font-mono font-semibold text-slate-200">{rec.waiting_time_sec}s</span>
                </div>
                <div>
                  <span className="text-slate-500">Delay Saved: </span>
                  <span className="font-mono font-bold text-emerald-400">-{rec.expected_delay_reduction_min} min</span>
                </div>
              </div>

              <div className="flex items-center gap-1 text-slate-400">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs font-mono">Confidence: {Math.round(rec.confidence_score * 100)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
