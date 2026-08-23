import React, { useState } from 'react';
import { HelpCircle, ChevronDown, ChevronUp, FileText, CheckCircle } from 'lucide-react';

export const PrototypeAssumptionsPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const assumptions = [
    { title: 'Logical Resource Mapping', detail: 'Track/resource assignments are modeled as logical directional resources (DOWN_SLOW, DOWN_FAST, DEFAULT) where infrastructure source data does not identify individual physical track IDs.' },
    { title: 'Modeled Safety Headway', detail: 'Safety headway (60s / 120s buffer) is a modeled parameter enforced as minimum interval spacing between consecutive block segment occupancies.' },
    { title: 'Signal & Interlocking Scope', detail: 'Physical signal aspect control and interlocking logic routes are not modeled in graph edge transitions.' },
    { title: 'Platform Line Assignment', detail: 'Station platforms are modeled as capacity constraints; individual physical track switching and platform line numbers are not modeled.' },
    { title: 'Logical Overtake & Crossovers', detail: 'Crossover track geometry and physical switches are represented as parallel logical track resource choices rather than physical track switches.' },
    { title: 'Offline Observation Telemetry', detail: 'Train movement telemetry is replayed from pre-fetched RailRadar observation snapshots to guarantee quota-safe, 100% offline demonstration reliability.' },
  ];

  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800/80 overflow-hidden shadow-lg">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between hover:bg-slate-800/40 transition text-left"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <HelpCircle className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Prototype Assumptions & Scientific Credibility Scope</h3>
            <p className="text-[11px] text-slate-400">Click to expand explicit technical assumptions & system boundaries</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            {assumptions.length} Modeled Assumptions
          </span>
          {isOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-4 pt-0 border-t border-slate-800/60 space-y-3 bg-slate-950/40">
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>
              Explicitly identifying technical assumptions ensures complete scientific credibility during competition judging and technical audit.
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {assumptions.map((a, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-slate-900/90 border border-slate-800/80 space-y-1">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>{a.title}</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed pl-5">{a.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
