import React from 'react';
import { RefreshCw, Play, Zap, Activity } from 'lucide-react';

interface TopNavProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  systemStatus: string;
  simTime: string;
  tickCount: number;
  lastUpdated: string;
  onRefresh: () => void;
  onStartDemo: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  activeTab,
  setActiveTab,
  systemStatus,
  simTime,
  tickCount,
  lastUpdated,
  onRefresh,
  onStartDemo,
}) => {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'network', label: 'Live Network' },
    { id: 'schedule', label: 'Train Schedule' },
    { id: 'recommendations', label: 'AI Recommendations' },
    { id: 'analytics', label: 'Analytics' },
    { id: 'simulation', label: 'Incident Simulator' },
  ];

  const isConnected = systemStatus === 'CONNECTED' || systemStatus === 'ONLINE';

  return (
    <header className="top-nav-bar flex flex-wrap items-center justify-between px-6 py-3 bg-slate-950/95 border-b border-slate-800 shadow-xl gap-4">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-inner">
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <h1 className="text-lg font-extrabold text-slate-100 tracking-tight leading-none">
              TRAC
            </h1>
            <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider mt-1">
              Train Rescheduling and Allocation Core
            </p>
          </div>
        </div>

        <nav className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === t.id
                  ? 'bg-emerald-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 text-xs font-bold transition shadow-sm"
          onClick={onStartDemo}
          title="Start Competition Demo Walkthrough"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Demo Flow</span>
        </button>

        {/* Backend Status Indicator */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold ${
            isConnected
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
          <span>{isConnected ? '🟢 SYSTEM CONNECTED' : '🔴 SYSTEM DISCONNECTED'}</span>
        </div>

        <button
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition"
          onClick={onRefresh}
          title="Refresh System Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
