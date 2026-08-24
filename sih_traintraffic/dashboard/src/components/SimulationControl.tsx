import React, { useState } from 'react';
import type { SimulationState } from '../types/railway';
import { apiService } from '../services/apiService';
import { Play, Pause, AlertTriangle, Zap, Train, Clock, RefreshCw, Cpu, FastForward } from 'lucide-react';
import confetti from 'canvas-confetti';

interface SimulationControlProps {
  simState?: SimulationState | null;
  onStateUpdate?: (newState: SimulationState) => void;
  onRunOptimization?: () => Promise<void>;
}

export const SimulationControl: React.FC<SimulationControlProps> = ({
  simState,
  onStateUpdate,
  onRunOptimization,
}) => {
  const [isSolving, setIsSolving] = useState(false);
  const [speed, setSpeed] = useState(simState?.speed_multiplier || 1);
  const isRunning = simState?.is_running ?? true;

  const handleAction = async (action: string, payload?: any) => {
    try {
      const updated = await apiService.sendSimulationControl(action, payload);
      if (onStateUpdate) onStateUpdate(updated);
    } catch (e) {
      console.error('Error executing control action:', e);
    }
  };

  const handleOptimize = async () => {
    setIsSolving(true);
    try {
      if (onRunOptimization) {
        await onRunOptimization();
      } else {
        await apiService.runOptimization();
        const updated = await apiService.fetchSimulationState();
        if (onStateUpdate) onStateUpdate(updated);
      }

      confetti({
        particleCount: 90,
        spread: 80,
        origin: { y: 0.6 },
      });
    } catch (e) {
      console.error(e);
    } finally {
      setIsSolving(false);
    }
  };

  return (
    <div className="w-full p-5 rounded-2xl bg-slate-900/95 border border-slate-800 shadow-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-3 gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-extrabold text-slate-100 tracking-tight">
              LIVE INCIDENT SIMULATOR
            </h2>
            <p className="text-xs text-slate-400">
              Inject real-time track disruptions, signal failures, or train delays and trigger OR-Tools CP-SAT re-optimization
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Speed Selector */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
            <FastForward className="w-3.5 h-3.5 text-slate-400 ml-1" />
            {[1, 2, 5, 10].map((s) => (
              <button
                key={s}
                onClick={() => {
                  setSpeed(s);
                  handleAction('speed', { speed_multiplier: s });
                }}
                className={`px-2 py-0.5 rounded font-bold transition ${
                  speed === s ? 'bg-cyan-500 text-slate-950 shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          {/* Start / Pause Button */}
          <button
            onClick={() => handleAction(isRunning ? 'pause' : 'start')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold transition shadow ${
              isRunning
                ? 'bg-amber-500/20 border border-amber-500/40 text-amber-400 hover:bg-amber-500/30'
                : 'bg-emerald-500 border border-emerald-400 text-slate-950 hover:bg-emerald-400'
            }`}
          >
            {isRunning ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>{isRunning ? 'PAUSE SIM' : 'START SIM'}</span>
          </button>
        </div>
      </div>

      {/* Interactive Action Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* 1. BLOCK TRACK */}
        <button
          onClick={() => handleAction('block_track', { blocked_section: 'BY_DR' })}
          className={`flex flex-col items-center justify-center p-3.5 rounded-xl border text-center transition-all ${
            simState?.track_blocked
              ? 'bg-rose-500/20 border-rose-500 text-rose-300 ring-2 ring-rose-500/40 animate-pulse'
              : 'bg-slate-950/80 border-slate-800 text-slate-300 hover:border-rose-500/50 hover:bg-rose-500/10'
          }`}
        >
          <AlertTriangle className="w-5 h-5 text-rose-400 mb-1.5" />
          <span className="text-xs font-bold">⚡ BLOCK TRACK</span>
          <span className="text-[10px] text-slate-400 mt-0.5">Dadar Fast Line</span>
        </button>

        {/* 2. SIGNAL FAILURE */}
        <button
          onClick={() => handleAction('signal_failure')}
          className="flex flex-col items-center justify-center p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 hover:border-amber-500/50 hover:bg-amber-500/10 transition-all"
        >
          <Zap className="w-5 h-5 text-amber-400 mb-1.5" />
          <span className="text-xs font-bold">⚠️ SIGNAL FAILURE</span>
          <span className="text-[10px] text-slate-400 mt-0.5">Kurla Crossover</span>
        </button>

        {/* 3. ADD PRIORITY TRAIN */}
        <button
          disabled
          title="No fetched Vande Bharat observation available in historical datasets"
          className="flex flex-col items-center justify-center p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-500 cursor-not-allowed opacity-60 transition-all"
        >
          <Train className="w-5 h-5 text-slate-600 mb-1.5" />
          <span className="text-xs font-bold">🚆 ADD PRIORITY TRAIN</span>
          <span className="text-[10px] text-slate-500 mt-0.5">No fetched service available</span>
        </button>

        {/* 4. INDUCE DELAY */}
        <button
          onClick={() => handleAction('induce_delay', { train_id: 'T104', delay_minutes: 10.0 })}
          className="flex flex-col items-center justify-center p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 hover:border-indigo-500/50 hover:bg-indigo-500/10 transition-all"
        >
          <Clock className="w-5 h-5 text-indigo-400 mb-1.5" />
          <span className="text-xs font-bold">⏱ INDUCE DELAY</span>
          <span className="text-[10px] text-slate-400 mt-0.5">+10 Min on T104</span>
        </button>

        {/* 5. RUN CP-SAT OPTIMIZATION */}
        <button
          onClick={handleOptimize}
          disabled={isSolving}
          className="flex flex-col items-center justify-center p-3.5 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-700 text-slate-950 border border-emerald-400 shadow-lg hover:brightness-110 transition-all disabled:opacity-50"
        >
          <Cpu className={`w-5 h-5 text-slate-950 mb-1.5 ${isSolving ? 'animate-spin' : ''}`} />
          <span className="text-xs font-extrabold tracking-tight">
            {isSolving ? 'SOLVING CP-SAT...' : '⚡ RUN CP-SAT OPTIMIZE'}
          </span>
          <span className="text-[10px] text-slate-900 font-semibold mt-0.5">OR-Tools Solver</span>
        </button>

        {/* 6. RESET SIMULATION */}
        <button
          onClick={() => handleAction('reset')}
          className="flex flex-col items-center justify-center p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 hover:border-slate-600 hover:bg-slate-800/50 transition-all"
        >
          <RefreshCw className="w-5 h-5 text-slate-400 mb-1.5" />
          <span className="text-xs font-bold">↻ RESET SIM</span>
          <span className="text-[10px] text-slate-400 mt-0.5">Clean Baseline</span>
        </button>
      </div>

      {/* Disruption Alert Notice when Track Blocked */}
      {simState?.track_blocked && (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/40 text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 animate-bounce" />
            <span>
              <strong>ACTIVE TRACK BLOCKAGE:</strong> Dadar Junction Fast Line (BY_DR). Trains T104 & T201 halted!
            </span>
          </div>
          <button
            onClick={handleOptimize}
            className="px-3 py-1 rounded-lg bg-rose-500 text-slate-950 font-bold hover:bg-rose-400 transition"
          >
            Trigger CP-SAT Solver Now ➔
          </button>
        </div>
      )}
    </div>
  );
};
