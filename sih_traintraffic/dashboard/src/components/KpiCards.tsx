import React from 'react';
import type { KpiMetrics } from '../types/railway';
import { Train, TrendingUp, Clock, Cpu, ShieldCheck, AlertOctagon } from 'lucide-react';

interface KpiCardsProps {
  metrics: KpiMetrics;
  lastUpdated?: string;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ metrics, lastUpdated }) => {
  const cards = [
    {
      title: 'ACTIVE TRAINS',
      value: `${metrics.active_trains}`,
      unit: 'services',
      subBadge: (
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
          ● Live Tracking
        </span>
      ),
      icon: Train,
      iconBg: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    },
    {
      title: 'THROUGHPUT',
      value: `${metrics.throughput_trains_per_hr}`,
      unit: 'trains/hr',
      subBadge: (
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-cyan-400">
          Live Derived
        </span>
      ),
      icon: Cpu,
      iconBg: 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20',
    },
    {
      title: 'AVERAGE DELAY',
      value: `${metrics.average_delay_min}`,
      unit: 'min',
      subBadge: (
        <span
          className={`inline-flex items-center gap-1 text-[11px] font-semibold ${
            metrics.average_delay_min > 5.0 ? 'text-rose-400' : 'text-emerald-400'
          }`}
        >
          {metrics.average_delay_min > 5.0 ? '⚠️ High Latency' : 'Optimal Flow'}
        </span>
      ),
      icon: Clock,
      iconBg: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20',
    },
    {
      title: 'TRACK UTILIZATION',
      value: `${metrics.track_utilization_pct}`,
      unit: '%',
      subBadge: (
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
          Corridor Capacity
        </span>
      ),
      icon: TrendingUp,
      iconBg: 'bg-teal-500/10 text-teal-400 border border-teal-500/20',
    },
    {
      title: 'CONFLICTS DETECTED',
      value: `${metrics.conflicts_detected}`,
      unit: 'active',
      subBadge: (
        <span
          className={`text-[11px] font-semibold ${
            metrics.conflicts_detected > 0 ? 'text-amber-400 animate-pulse' : 'text-slate-400'
          }`}
        >
          {metrics.conflicts_detected > 0 ? '⚠️ Interlocking Alert' : 'No Conflicts'}
        </span>
      ),
      icon: AlertOctagon,
      iconBg: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    },
    {
      title: 'CONFLICTS RESOLVED',
      value: `${metrics.conflicts_resolved}`,
      unit: 'cleared',
      subBadge: (
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
          <ShieldCheck className="w-3 h-3" /> CP-SAT Solved
        </span>
      ),
      icon: ShieldCheck,
      iconBg: 'bg-purple-500/10 text-purple-400 border border-purple-500/20',
    },
  ];

  return (
    <div className="space-y-2">
      {lastUpdated && (
        <div className="flex items-center justify-end px-1 text-[11px] font-mono text-slate-400">
          <span>Last updated: </span>
          <span className="ml-1.5 font-bold text-slate-200">{lastUpdated}</span>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 lg:gap-4 w-full">
        {cards.map((card, idx) => {
          const IconComponent = card.icon;
          return (
            <div
              key={idx}
              className="flex flex-col justify-between p-4 rounded-xl bg-slate-900/90 border border-slate-800/90 shadow-xl hover:border-slate-700/80 transition-all duration-200"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] sm:text-[11px] font-bold text-slate-400 tracking-wider uppercase">
                  {card.title}
                </span>
                <div className={`p-2 rounded-lg ${card.iconBg}`}>
                  <IconComponent className="w-4 h-4" />
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-1.5 mb-1">
                  <span className="text-2xl sm:text-3xl font-extrabold text-slate-100 font-mono tracking-tight">
                    {card.value}
                  </span>
                  {card.unit && <span className="text-xs text-slate-400 font-mono">{card.unit}</span>}
                </div>
                <div>{card.subBadge}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
