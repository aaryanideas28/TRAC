import React, { useState } from 'react';
import { VALIDATED_BENCHMARK } from '../services/apiService';
import { BarChart3, LineChart as LineChartIcon, ShieldCheck, ArrowRight, Activity } from 'lucide-react';
import {
  ResponsiveContainer,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
  AreaChart,
  Area,
} from 'recharts';

export const AnalyticsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'benchmark' | 'simulation'>('benchmark');
  const bm = VALIDATED_BENCHMARK;

  const hourlyThroughputData = [
    { time: '08:00', baseline: 14, optimized: 18 },
    { time: '09:00', baseline: 12, optimized: 17 },
    { time: '10:00', baseline: 15, optimized: 21 },
    { time: '11:00', baseline: 13, optimized: 19 },
    { time: '12:00', baseline: 16, optimized: 22 },
    { time: '13:00', baseline: 15, optimized: 24 },
  ];

  const delayReductionData = [
    { train: 'T101 Express', baseline: 8.2, optimized: 1.5 },
    { train: 'T104 Superfast', baseline: 6.5, optimized: 1.2 },
    { train: 'T218 Local', baseline: 12.4, optimized: 3.1 },
    { train: 'T305 Freight', baseline: 18.0, optimized: 5.4 },
    { train: 'T201 Fast Local', baseline: 7.1, optimized: 1.8 },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header & Data Type Selector */}
      <div className="flex items-center justify-between card-container">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">Section Analytics & Performance Metrics</h2>
            <p className="text-xs text-slate-400">Quantitative Benchmarks & Throughput Evaluation</p>
          </div>
        </div>

        {/* Data Type Selector Legend */}
        <div className="flex items-center rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
          <button
            onClick={() => setActiveTab('benchmark')}
            className={`px-3 py-1.5 rounded-md font-bold transition flex items-center gap-1.5 ${
              activeTab === 'benchmark'
                ? 'bg-emerald-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Validated Benchmark</span>
          </button>
          <button
            onClick={() => setActiveTab('simulation')}
            className={`px-3 py-1.5 rounded-md font-bold transition flex items-center gap-1.5 ${
              activeTab === 'simulation'
                ? 'bg-cyan-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Simulation Scenario</span>
          </button>
        </div>
      </div>

      {activeTab === 'benchmark' ? (
        /* VALIDATED BENCHMARK VIEW */
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Card 1 */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-emerald-500/30 space-y-2">
              <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Total Completion Delay</span>
              <div className="flex items-baseline justify-between font-mono">
                <span className="text-sm text-slate-400 line-through">{bm.legacy_baseline.total_completion_delay_min}m</span>
                <ArrowRight className="w-4 h-4 text-slate-500" />
                <span className="text-2xl font-extrabold text-emerald-400">{bm.infrastructure_aware.total_completion_delay_min}m</span>
              </div>
              <div className="text-xs font-bold text-emerald-400 bg-emerald-500/10 py-1 px-2.5 rounded text-center border border-emerald-500/20">
                ↓ 2.34% Total Network Delay Saved
              </div>
            </div>

            {/* Card 2 */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-cyan-500/30 space-y-2">
              <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Optimizer Added Hold</span>
              <div className="flex items-baseline justify-between font-mono">
                <span className="text-sm text-slate-400 line-through">{bm.legacy_baseline.additional_hold_min}m</span>
                <ArrowRight className="w-4 h-4 text-slate-500" />
                <span className="text-2xl font-extrabold text-cyan-400">{bm.infrastructure_aware.additional_hold_min}m</span>
              </div>
              <div className="text-xs font-bold text-cyan-400 bg-cyan-500/10 py-1 px-2.5 rounded text-center border border-cyan-500/20">
                ↓ 40.41% Additional Hold Saved
              </div>
            </div>

            {/* Card 3 */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-indigo-500/30 space-y-2">
              <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Delay Variance</span>
              <div className="flex items-baseline justify-between font-mono">
                <span className="text-sm text-slate-400 line-through">{bm.legacy_baseline.delay_variance_min2}m²</span>
                <ArrowRight className="w-4 h-4 text-slate-500" />
                <span className="text-2xl font-extrabold text-indigo-400">{bm.infrastructure_aware.delay_variance_min2}m²</span>
              </div>
              <div className="text-xs font-bold text-indigo-400 bg-indigo-500/10 py-1 px-2.5 rounded text-center border border-indigo-500/20">
                ↓ 7.35% Delay Variance Reduction
              </div>
            </div>

            {/* Card 4 */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-amber-500/30 space-y-2">
              <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Modeled Conflicts</span>
              <div className="flex items-baseline justify-between font-mono">
                <span className="text-sm text-slate-400 line-through">{bm.legacy_baseline.modeled_conflicts}</span>
                <ArrowRight className="w-4 h-4 text-slate-500" />
                <span className="text-2xl font-extrabold text-amber-400">{bm.infrastructure_aware.modeled_conflicts}</span>
              </div>
              <div className="text-xs font-bold text-amber-400 bg-amber-500/10 py-1 px-2.5 rounded text-center border border-amber-500/20">
                ↓ 39.42% Modeled Conflicts Reduced
              </div>
            </div>
          </div>

          {/* Detailed Benchmark Table */}
          <div className="card-container space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Canonical 10-Train Infrastructure-Aware Benchmark Table</h3>
              <span className="text-xs font-mono text-emerald-400">Canonical Experiment Proof</span>
            </div>

            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-mono">
                <tr>
                  <th className="py-3 px-4">Evaluation Metric</th>
                  <th className="py-3 px-4">Single-Resource Baseline</th>
                  <th className="py-3 px-4">Infrastructure-Aware CP-SAT</th>
                  <th className="py-3 px-4">Net Improvement</th>
                  <th className="py-3 px-4">Verification Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                <tr className="hover:bg-slate-900/50">
                  <td className="py-3 px-4 font-sans font-semibold text-slate-200">Total Completion Delay</td>
                  <td className="py-3 px-4 text-slate-400">200.52 min</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold">195.82 min</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold">-4.7 min (-2.34%)</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold">VERIFIED EXPLICIT</td>
                </tr>
                <tr className="hover:bg-slate-900/50">
                  <td className="py-3 px-4 font-sans font-semibold text-slate-200">Optimizer-Added Hold Delay</td>
                  <td className="py-3 px-4 text-slate-400">19.55 min</td>
                  <td className="py-3 px-4 text-cyan-400 font-bold">11.65 min</td>
                  <td className="py-3 px-4 text-cyan-400 font-bold">-7.9 min (-40.41%)</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold">VERIFIED EXPLICIT</td>
                </tr>
                <tr className="hover:bg-slate-900/50">
                  <td className="py-3 px-4 font-sans font-semibold text-slate-200">Delay Variance</td>
                  <td className="py-3 px-4 text-slate-400">66.36 min²</td>
                  <td className="py-3 px-4 text-indigo-400 font-bold">61.48 min²</td>
                  <td className="py-3 px-4 text-indigo-400 font-bold">-4.88 min² (-7.35%)</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold">VERIFIED EXPLICIT</td>
                </tr>
                <tr className="hover:bg-slate-900/50">
                  <td className="py-3 px-4 font-sans font-semibold text-slate-200">Modeled Pairwise Conflicts</td>
                  <td className="py-3 px-4 text-slate-400">1,172 conflicts</td>
                  <td className="py-3 px-4 text-amber-400 font-bold">710 conflicts</td>
                  <td className="py-3 px-4 text-amber-400 font-bold">-462 (-39.42%)</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold">VERIFIED EXPLICIT</td>
                </tr>
                <tr className="hover:bg-slate-900/50">
                  <td className="py-3 px-4 font-sans font-semibold text-slate-200">Zero-Hold Trains</td>
                  <td className="py-3 px-4 text-slate-400">3 trains</td>
                  <td className="py-3 px-4 text-teal-400 font-bold">5 trains</td>
                  <td className="py-3 px-4 text-teal-400 font-bold">+2 trains (3 → 5)</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold">VERIFIED EXPLICIT</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* SIMULATION VIEW */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Throughput Progression */}
          <div className="card-container space-y-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <LineChartIcon className="w-4 h-4 text-cyan-400" />
              Hourly Section Throughput (Simulation Scenario)
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={hourlyThroughputData}>
                  <defs>
                    <linearGradient id="colorOpt" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                  <Legend />
                  <Area type="monotone" dataKey="optimized" name="With CP-SAT Optimization" stroke="#10b981" fillOpacity={1} fill="url(#colorOpt)" />
                  <Line type="monotone" dataKey="baseline" name="Baseline Manual Dispatch" stroke="#f43f5e" strokeDasharray="5 5" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Delay Reduction */}
          <div className="card-container space-y-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-emerald-400" />
              Per-Train Delay Mitigation (Simulation Scenario)
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={delayReductionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="train" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                  <Legend />
                  <Bar dataKey="baseline" name="Baseline Delay (min)" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="optimized" name="CP-SAT Optimized Delay (min)" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
