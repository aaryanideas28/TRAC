import React from 'react';
import type { MlPredictionState } from '../types/railway';
import { Brain, AlertCircle, CheckCircle } from 'lucide-react';

interface MlVisualizationPanelProps {
  mlPrediction?: MlPredictionState | null;
}

export const MlVisualizationPanel: React.FC<MlVisualizationPanelProps> = ({ mlPrediction }) => {
  const risk = mlPrediction?.congestion_risk || 'LOW';
  const prob = Math.round((mlPrediction?.congestion_prob || 0.12) * 100);
  const delayMin = mlPrediction?.predicted_delay_min || 0.5;
  const affectedCount = mlPrediction?.affected_trains_count || 0;
  const modelName = mlPrediction?.model_name || 'Random Forest Classifier (100 Trees)';

  const getRiskColor = (r: string) => {
    switch (r) {
      case 'HIGH':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      case 'MEDIUM':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      default:
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-slate-100">ML CONGESTION RISK PREDICTION</h3>
            <p className="text-xs text-slate-400">Scikit-Learn Random Forest Model • Central Line Telemetry</p>
          </div>
        </div>

        <span className="text-[10px] px-2.5 py-1 rounded-full bg-slate-950 border border-slate-800 font-mono text-indigo-300">
          {modelName}
        </span>
      </div>

      {/* Main Prediction Display */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Risk Level Badge */}
        <div className={`p-4 rounded-xl border flex flex-col justify-between ${getRiskColor(risk)}`}>
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Congestion Risk</span>
          <div className="flex items-center justify-between my-1">
            <span className="text-2xl font-black font-mono">{risk}</span>
            {risk === 'HIGH' ? <AlertCircle className="w-6 h-6 animate-pulse text-rose-400" /> : <CheckCircle className="w-6 h-6 text-emerald-400" />}
          </div>
          {/* Progress Bar */}
          <div className="w-full bg-slate-950/60 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                risk === 'HIGH' ? 'bg-rose-500' : risk === 'MEDIUM' ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.max(10, prob)}%` }}
            ></div>
          </div>
        </div>

        {/* Delay Prediction */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Predicted Delay Impact</span>
          <div className="my-1">
            <span className="text-2xl font-black font-mono text-slate-100">+{delayMin}</span>
            <span className="text-xs font-mono text-slate-400 ml-1">minutes</span>
          </div>
          <span className="text-[11px] text-slate-400">Bottleneck cascade projection</span>
        </div>

        {/* Affected Services */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Affected Train Services</span>
          <div className="my-1">
            <span className="text-2xl font-black font-mono text-slate-100">{affectedCount}</span>
            <span className="text-xs font-mono text-slate-400 ml-1">trains</span>
          </div>
          <span className="text-[11px] text-slate-400">Directly impacted by section</span>
        </div>
      </div>
    </div>
  );
};
