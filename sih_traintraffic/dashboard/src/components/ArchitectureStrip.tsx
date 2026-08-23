import React from 'react';
import { ArrowRight, Radio, Brain, GitFork, Cpu, ShieldCheck, Monitor } from 'lucide-react';

export const ArchitectureStrip: React.FC = () => {
  const steps = [
    { title: 'RailRadar Replay', desc: 'Captured Telemetry', icon: Radio, color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10' },
    { title: 'Random Forest', desc: 'Delay Risk Prediction', icon: Brain, color: 'text-purple-400 border-purple-500/30 bg-purple-500/10' },
    { title: 'Delay + Risk Signals', desc: 'Feature Generation', icon: GitFork, color: 'text-indigo-400 border-indigo-500/30 bg-indigo-500/10' },
    { title: 'Railway Graph', desc: 'Infrastructure Topology', icon: Cpu, color: 'text-blue-400 border-blue-500/30 bg-blue-500/10' },
    { title: 'OR-Tools CP-SAT', desc: 'Conflict-Free Solver', icon: ShieldCheck, color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' },
    { title: 'Web Dashboard', desc: 'Command Portal', icon: Monitor, color: 'text-teal-400 border-teal-500/30 bg-teal-500/10' },
  ];

  return (
    <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
        <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          End-to-End System Pipeline Architecture
        </h3>
        <span className="text-[11px] font-mono text-slate-400">SIH Technical Pipeline</span>
      </div>

      <div className="flex items-center justify-between overflow-x-auto py-1 gap-2">
        {steps.map((step, idx) => {
          const IconComp = step.icon;
          return (
            <React.Fragment key={idx}>
              <div className="flex-1 min-w-[130px] p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center gap-2.5 hover:border-slate-700 transition">
                <div className={`p-1.5 rounded-md border shrink-0 ${step.color}`}>
                  <IconComp className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-200">{step.title}</h4>
                  <p className="text-[10px] text-slate-400 line-clamp-1">{step.desc}</p>
                </div>
              </div>
              {idx < steps.length - 1 && <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
