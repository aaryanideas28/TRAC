import React, { useState } from 'react';
import type { Train } from '../types/railway';
import { Search, ArrowUpDown, Filter, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';

interface TrainScheduleTableProps {
  trains: Train[];
  onSelectTrain: (train: Train) => void;
}

export const TrainScheduleTable: React.FC<TrainScheduleTableProps> = ({ trains, onSelectTrain }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [filterStatus, setFilterStatus] = useState('All');
  const [sortField, setSortField] = useState<keyof Train>('scheduled_eta');
  const [sortAsc, setSortAsc] = useState(true);

  // Filter logic
  let filtered = trains.filter((t) => {
    const matchesSearch =
      t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.origin_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.destination_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'All' || t.type === filterType;
    const matchesStatus = filterStatus === 'All' || t.status === filterStatus;
    return matchesSearch && matchesType && matchesStatus;
  });

  // Sort logic
  filtered.sort((a, b) => {
    const valA = a[sortField] ?? '';
    const valB = b[sortField] ?? '';
    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  const handleSort = (field: keyof Train) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Moving':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 w-fit">
            <CheckCircle2 className="w-3 h-3" /> Moving
          </span>
        );
      case 'Waiting':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1 w-fit">
            <Clock className="w-3 h-3" /> Waiting
          </span>
        );
      case 'Delayed':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1 w-fit">
            <AlertTriangle className="w-3 h-3" /> Delayed
          </span>
        );
      case 'Conflict':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-400 border border-orange-500/30 flex items-center gap-1 w-fit">
            <AlertTriangle className="w-3 h-3" /> Conflict
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="card-container space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-100">Train Timetable Schedule</h2>
          <p className="text-xs text-slate-400">Replayed RailRadar Observations & Assigned Track Resources</p>
        </div>

        {/* Filter Controls Bar */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          {/* Search Input */}
          <div className="relative min-w-[200px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search train ID, name, station..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full py-1.5 pl-8 pr-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-700"
            />
          </div>

          {/* Type Filter */}
          <div className="flex items-center gap-1 bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-800">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-transparent text-slate-300 font-medium focus:outline-none"
            >
              <option value="All">All Types</option>
              <option value="Express">Express</option>
              <option value="Local">Local</option>
              <option value="Freight">Freight</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1 bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-800">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-transparent text-slate-300 font-medium focus:outline-none"
            >
              <option value="All">All Statuses</option>
              <option value="Moving">Moving</option>
              <option value="Waiting">Waiting</option>
              <option value="Delayed">Delayed</option>
              <option value="Conflict">Conflict</option>
            </select>
          </div>
        </div>
      </div>

      {/* Timetable Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/90 shadow-inner">
        <table className="w-full text-xs text-left">
          <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono border-b border-slate-800">
            <tr>
              <th className="py-3 px-4 cursor-pointer hover:text-slate-200" onClick={() => handleSort('id')}>
                <div className="flex items-center gap-1">
                  Train ID <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-3 px-4">Train Name</th>
              <th className="py-3 px-4">Service Type</th>
              <th className="py-3 px-4">Origin → Destination</th>
              <th className="py-3 px-4 cursor-pointer hover:text-slate-200" onClick={() => handleSort('scheduled_eta')}>
                <div className="flex items-center gap-1">
                  Scheduled ETA <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-3 px-4 cursor-pointer hover:text-slate-200" onClick={() => handleSort('delay_min')}>
                <div className="flex items-center gap-1">
                  Delay (min) <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-3 px-4">Assigned Resource</th>
              <th className="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
            {filtered.map((t) => (
              <tr
                key={t.id}
                onClick={() => onSelectTrain(t)}
                className="hover:bg-slate-900/60 cursor-pointer transition"
              >
                <td className="py-3 px-4 font-bold text-cyan-400">{t.id}</td>
                <td className="py-3 px-4 font-sans font-semibold text-slate-200">{t.name}</td>
                <td className="py-3 px-4 font-sans">{t.type}</td>
                <td className="py-3 px-4 font-sans text-slate-400">
                  {t.origin_name} → <span className="text-slate-200">{t.destination_name}</span>
                </td>
                <td className="py-3 px-4">{t.scheduled_eta}</td>
                <td className="py-3 px-4">
                  {t.delay_min > 0 ? (
                    <span className="text-amber-400 font-bold">+{t.delay_min} min</span>
                  ) : (
                    <span className="text-emerald-400">On Time</span>
                  )}
                </td>
                <td className="py-3 px-4 text-cyan-300 font-semibold">{t.assigned_track}</td>
                <td className="py-3 px-4">{getStatusBadge(t.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
