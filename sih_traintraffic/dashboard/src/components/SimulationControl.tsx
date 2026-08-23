import React, { useState } from 'react';
import type { SimulationConfig } from '../types/railway';
import { Cpu, ShieldCheck, RefreshCw, Sparkles, Flame } from 'lucide-react';
import confetti from 'canvas-confetti';

interface SimulationControlProps {
  onRunOptimization: (config: SimulationConfig) => Promise<void>;
}

export const SimulationControl: React.FC<SimulationControlProps> = ({ onRunOptimization }) => {
  const [scenario, setScenario] = useState('Peak Hour');
  const [density, setDensity] = useState('High');
  const [trackStatus, setTrackStatus] = useState('Available');
  const [blockedSection] = useState('Dadar Junction');
  const [priorityTrain, setPriorityTrain] = useState('T101');
  const [isCalculating, setIsCalculating] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);

  const scenariosList = [
    { id: 'Normal', title: 'Normal Operational Flow', desc: 'Standard timetabled traffic sequence across all tracks.' },
    { id: 'Peak Hour', title: 'Peak Hour Rush', desc: 'High-density suburban service frequency with 120s headways.' },
    { id: 'Heavy Congestion', title: 'Heavy Congestion Spike', desc: 'Downstream bottleneck with multiple delayed freight & local trains.' },
    { id: 'Train Delay', title: 'Primary Train Delay Cascade', desc: 'Express service delayed by 15 mins causing cascading conflicts.' },
    { id: 'Track Blockage', title: 'Track Blockage / Maintenance', desc: 'One main line blocked; traffic rerouted via dual/loop tracks.' },
    { id: 'Priority Train', title: 'VIP Express Priority Clearance', desc: 'Emergency priority corridor override for Superfast train.' },
  ];

  const handleRun = async () => {
    setIsCalculating(true);
    setIsCompleted(false);

    try {
      await onRunOptimization({
        scenario,
        density,
        track_status: trackStatus,
        blocked_section: blockedSection,
        priority_train_id: priorityTrain,
      });

      // Celebration Confetti
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
      });

      setIsCompleted(true);
    } catch (e) {
      console.error(e);
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <div className="card-container space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">Traffic Simulation & Scenario Control</h2>
            <p className="text-xs text-slate-400">Configure Railway Traffic Conditions & Trigger OR-Tools CP-SAT Solver</p>
          </div>
        </div>

        <span className="text-xs px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-300 font-mono">
          Engine: Google OR-Tools CP-SAT
        </span>
      </div>

      {/* Scenario Grid Selectors */}
      <div>
        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-3">
          1. Select Traffic Scenario
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {scenariosList.map((s) => (
            <button
              key={s.id}
              onClick={() => setScenario(s.id)}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                scenario === s.id
                  ? 'bg-emerald-500/10 border-emerald-500/60 text-slate-100 ring-1 ring-emerald-500/30'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-bold">{s.title}</span>
                {scenario === s.id && <Sparkles className="w-4 h-4 text-emerald-400" />}
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{s.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Parameter Fine-Tuning Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
        {/* Density Selector */}
        <div>
          <label className="text-slate-400 font-bold block mb-1.5">Traffic Density</label>

          <div className="flex rounded-lg bg-slate-900 p-1 border border-slate-800">
            {['Low', 'Medium', 'High'].map((d) => (
              <button
                key={d}
                onClick={() => setDensity(d)}
                className={`flex-1 py-1.5 rounded-md font-semibold text-center transition ${
                  density === d ? 'bg-emerald-500 text-slate-950 shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Track Status */}
        <div>
          <label className="text-slate-400 font-bold block mb-1.5">Track Infrastructure Status</label>
          <div className="flex rounded-lg bg-slate-900 p-1 border border-slate-800">
            {['Available', 'Blocked'].map((st) => (
              <button
                key={st}
                onClick={() => setTrackStatus(st)}
                className={`flex-1 py-1.5 rounded-md font-semibold text-center transition ${
                  trackStatus === st
                    ? st === 'Blocked'
                      ? 'bg-rose-500 text-white'
                      : 'bg-emerald-500 text-slate-950'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Priority Train */}
        <div>
          <label className="text-slate-400 font-bold block mb-1.5">Select Priority Train</label>
          <select
            value={priorityTrain}
            onChange={(e) => setPriorityTrain(e.target.value)}
            className="w-full py-2 px-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 font-medium focus:outline-none"
          >
            <option value="T101">T101 Express (CSMT - Thane)</option>
            <option value="T104">T104 Superfast (CSMT - Kalyan)</option>
            <option value="T201">T201 Fast Local (CSMT - Kasara)</option>
            <option value="T218">T218 Local (CSMT - Thane)</option>
          </select>
        </div>
      </div>

      {/* Prominent Action Button */}
      <div className="pt-2">
        <button
          onClick={handleRun}
          disabled={isCalculating}
          className={`w-full py-4 rounded-xl font-extrabold text-base tracking-wide flex items-center justify-center gap-3 transition shadow-xl ${
            isCalculating
              ? 'bg-slate-800 text-slate-400 cursor-not-allowed border border-slate-700'
              : 'bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-slate-950 hover:scale-[1.01] active:scale-[0.99]'
          }`}
        >
          {isCalculating ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin text-emerald-400" />
              <span>AI is calculating optimal traffic sequence...</span>
            </>
          ) : (
            <>
              <Flame className="w-5 h-5 fill-current text-slate-950" />
              <span>RUN AI OPTIMIZATION</span>
            </>
          )}
        </button>

        {isCompleted && (
          <div className="mt-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold text-center flex items-center justify-center gap-2">
            <ShieldCheck className="w-4 h-4" />
            <span>Optimization Complete! Railway graph, timetable, and recommendations updated with OR-Tools solution.</span>
          </div>
        )}
      </div>
    </div>
  );
};
