import React from 'react';
import type { Train } from '../types/railway';
import { X, Train as TrainIcon, Navigation, Clock, ArrowRight, Gauge } from 'lucide-react';

interface TrainDetailModalProps {
  train: Train | null;
  onClose: () => void;
}

export const TrainDetailModal: React.FC<TrainDetailModalProps> = ({ train, onClose }) => {
  if (!train) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Moving':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">● Moving</span>;
      case 'Waiting':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">● Waiting</span>;
      case 'Delayed':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">● Delayed</span>;
      case 'Conflict':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 animate-pulse">● Conflict / Risk</span>;
      default:
        return null;
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'High':
        return <span className="text-xs font-bold text-rose-400">HIGH PRIORITY</span>;
      case 'Medium':
        return <span className="text-xs font-semibold text-amber-400">MEDIUM PRIORITY</span>;
      default:
        return <span className="text-xs text-slate-400">LOW PRIORITY</span>;
    }
  };

  return (
    <div className="modal-overlay backdrop-blur-sm" onClick={onClose}>
      <div className="modal-content text-slate-100 border border-slate-700/60 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700/50 bg-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <TrainIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-100">{train.name}</h3>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">{train.id}</span>
              </div>
              <p className="text-xs text-slate-400">{train.type} Service • {getPriorityBadge(train.priority)}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 text-sm">
          {/* Status & Track Banner */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Current Status</span>
              {getStatusBadge(train.status)}
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 block mb-0.5">Assigned Track</span>
              <span className="font-medium text-cyan-400">{train.assigned_track}</span>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                <Navigation className="w-3.5 h-3.5 text-emerald-400" />
                <span>Location</span>
              </div>
              <span className="font-semibold text-slate-200">{train.current_location_name}</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
                <span>Destination</span>
              </div>
              <span className="font-semibold text-slate-200">{train.destination_name}</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                <Gauge className="w-3.5 h-3.5 text-indigo-400" />
                <span>Current Speed</span>
              </div>
              <span className="font-bold text-slate-100 text-base">{train.speed_kmh} <span className="text-xs font-normal text-slate-400">km/h</span></span>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>Current Delay</span>
              </div>
              <span className={`font-bold text-base ${train.delay_min > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {train.delay_min > 0 ? `+${train.delay_min} min` : 'On Time'}
              </span>
            </div>
          </div>

          {/* Timetable Comparison */}
          <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Timetable Schedule</h4>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Scheduled Arrival:</span>
              <span className="font-mono text-slate-200 font-medium">{train.scheduled_eta}</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Expected Arrival:</span>
              <span className="font-mono text-cyan-300 font-bold">{train.expected_eta}</span>
            </div>
          </div>

          {/* Route Segment Visualizer */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Route Stations</h4>
            <div className="flex items-center gap-1 overflow-x-auto pb-1 text-xs font-mono">
              {train.route.map((st, i) => (
                <React.Fragment key={st}>
                  <span className={`px-2 py-1 rounded ${st === train.current_location ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40' : 'bg-slate-800 text-slate-400'}`}>
                    {st}
                  </span>
                  {i < train.route.length - 1 && <span className="text-slate-600">→</span>}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3.5 border-t border-slate-700/50 bg-slate-800/80 text-right">
          <button onClick={onClose} className="px-4 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-white font-medium text-xs transition">
            Close Panel
          </button>
        </div>
      </div>
    </div>
  );
};
