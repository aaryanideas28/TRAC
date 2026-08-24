import React, { useState } from 'react';
import type { StationNode, Train } from '../types/railway';
import { Layers, AlertTriangle, Info } from 'lucide-react';

interface LiveRailwayNetworkProps {
  nodes: StationNode[];
  trains: Train[];
  onSelectTrain: (train: Train) => void;
  selectedTrainId?: string;
  isTrackBlocked?: boolean;
}

// 19 Central Line Stations with real authentic data & fast/slow individuality
export const CORRIDOR_STATIONS = [
  { code: 'CSMT', name: 'Chhatrapati Shivaji Maharaj Terminus', km: 0.0, isFast: true, isSlow: true, hasLoop: true, posX: 55, pf: 'PF 1-7', type: 'Major Terminus', infra: '4-Track Sea level terminus / Historic architecture constraints' },
  { code: 'MSD', name: 'Masjid (Bombay Masjid)', km: 1.4, isFast: false, isSlow: true, hasLoop: false, posX: 110, pf: 'PF 1-2', type: 'Slow Only', infra: 'High-density urban sprawl / Low vertical clearance ROBs' },
  { code: 'SNRD', name: 'Sandhurst Road', km: 2.7, isFast: false, isSlow: true, hasLoop: false, posX: 165, pf: 'PF 1-2', type: 'Slow Only', infra: 'Double-Decker Elevated Intersect / Harbour line crosses overhead' },
  { code: 'BY', name: 'Byculla', km: 4.0, isFast: true, isSlow: true, hasLoop: false, posX: 220, pf: 'PF 1-4', type: 'Fast & Slow Hub', infra: 'Urban bottleneck / British-era structural stone walls' },
  { code: 'CHG', name: 'Chinchpokli', km: 5.2, isFast: false, isSlow: true, hasLoop: false, posX: 275, pf: 'PF 1-2', type: 'Slow Only', infra: 'Arthur Road ROB constriction / At-Grade' },
  { code: 'CRD', name: 'Currey Road', km: 6.3, isFast: false, isSlow: true, hasLoop: false, posX: 330, pf: 'PF 1-2', type: 'Slow Only', infra: 'Dense commercial structural limits / At-Grade' },
  { code: 'PR', name: 'Parel', km: 7.7, isFast: false, isSlow: true, hasLoop: true, posX: 385, pf: 'PF 1-2', type: 'Slow + Siding', infra: 'Elphinstone-Parel ROB bridge constraints / Reversing siding' },
  { code: 'DR', name: 'Dadar Junction', km: 8.8, isFast: true, isSlow: true, hasLoop: true, posX: 440, pf: 'PF 1-4', type: 'Major Interlocking Hub', infra: 'Western Line intersection / Tilak Bridge constraint & Loop sidings' },
  { code: 'MTN', name: 'Matunga', km: 10.2, isFast: false, isSlow: true, hasLoop: true, posX: 495, pf: 'PF 1-2', type: 'Slow Only', infra: 'Close proximity to Central Railway Carriage Workshop sidings' },
  { code: 'SION', name: 'Sion', km: 11.9, isFast: false, isSlow: true, hasLoop: false, posX: 550, pf: 'PF 1-2', type: 'Slow Only', infra: 'Approaching low-lying Mithi River floodplain cutting' },
  { code: 'CLA', name: 'Kurla Junction', km: 14.7, isFast: true, isSlow: true, hasLoop: true, posX: 605, pf: 'PF 1-6', type: 'Major Junction', infra: '6-Track Junction / Mithi River Bridge / EMU Car Shed Loops' },
  { code: 'VVH', name: 'Vidyavihar', km: 16.4, isFast: false, isSlow: true, hasLoop: false, posX: 660, pf: 'PF 1-2', type: 'Slow Only', infra: 'Transition zone to Suburbs / 6-Track baseline' },
  { code: 'GC', name: 'Ghatkopar', km: 18.2, isFast: true, isSlow: true, hasLoop: true, posX: 715, pf: 'PF 1-4', type: 'Metro Interchange Hub', infra: 'High utility crossover bridge integration & Loop sidings' },
  { code: 'VK', name: 'Vikhroli', km: 21.1, isFast: false, isSlow: true, hasLoop: false, posX: 770, pf: 'PF 1-2', type: 'Slow Only', infra: 'Industrial land borders / Foothill drainage runoffs' },
  { code: 'KJRD', name: 'Kanjur Marg', km: 22.8, isFast: false, isSlow: true, hasLoop: false, posX: 825, pf: 'PF 1-2', type: 'Slow Only', infra: 'Suburban expansion zone / 6-Track corridor' },
  { code: 'BND', name: 'Bhandup', km: 24.5, isFast: false, isSlow: true, hasLoop: false, posX: 880, pf: 'PF 1-2', type: 'Slow Only', infra: 'Water pipeline bridge crossing limits' },
  { code: 'NHU', name: 'Nahur', km: 26.6, isFast: false, isSlow: true, hasLoop: false, posX: 935, pf: 'PF 1-2', type: 'Slow Only', infra: 'Mulund-Goregaon Link Road planned flyovers' },
  { code: 'MLND', name: 'Mulund', km: 28.5, isFast: true, isSlow: true, hasLoop: false, posX: 990, pf: 'PF 1-4', type: 'Fast & Slow Hub', infra: 'Approaching Parsik Hill foothills baseline' },
  { code: 'TNA', name: 'Thane', km: 32.7, isFast: true, isSlow: true, hasLoop: true, posX: 1045, pf: 'PF 1-10', type: 'Major Junction Terminus', infra: '6-Track Major Junction Terminus / Trans-Harbour Loop & Parsik Tunnel gateway' },
];

export const LiveRailwayNetwork: React.FC<LiveRailwayNetworkProps> = ({
  nodes,
  trains,
  onSelectTrain,
  selectedTrainId,
  isTrackBlocked = false,
}) => {
  const [hoveredTrain, setHoveredTrain] = useState<Train | null>(null);
  const [hoveredStation, setHoveredStation] = useState<typeof CORRIDOR_STATIONS[0] | null>(null);
  const [showLoopInfo, setShowLoopInfo] = useState(false);
  const [showStationLegend, setShowStationLegend] = useState(true);
  const [filterMode, setFilterMode] = useState<'ALL' | 'FAST' | 'SLOW' | 'LOOP'>('ALL');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Moving':
        return '#10b981'; // Emerald Green
      case 'Waiting':
        return '#f59e0b'; // Amber Yellow
      case 'Delayed':
        return '#ef4444'; // Red
      case 'Conflict':
        return '#ef4444'; // Red
      default:
        return '#10b981';
    }
  };

  // Node position lookup map with 19 stations
  const nodePosMap: Record<string, number> = {};
  CORRIDOR_STATIONS.forEach((stn) => {
    nodePosMap[stn.code] = stn.posX;
  });
  nodes.forEach((n) => {
    if (n.pos_x && nodePosMap[n.station_code] === undefined) {
      nodePosMap[n.station_code] = n.pos_x;
    }
  });

  // Exactly 7 Fast stations for Fast line stopping pattern
  const FAST_STOPS = ['CSMT', 'BY', 'DR', 'CLA', 'GC', 'MLND', 'TNA'];
  const FULL_CORRIDOR_ROUTE = CORRIDOR_STATIONS.map((s) => s.code);

  // Compute interpolated and collision-free train positions with safety headway
  const getPositionedTrains = (): Array<Train & { x: number; y: number }> => {
    // 1. Calculate raw target X coordinate for each train
    const rawList = trains.map((train) => {
      const isFast = train.assigned_track.includes('Fast') || train.type === 'Fast Local' || train.type === 'Express';
      const isLoop = train.assigned_track.includes('Loop');

      let y = isLoop ? 305 : isFast ? 215 : 125;
      let rawX = 55;

      if (isLoop) {
        // Dedicated Loop Siding Berths (sitting directly on Loop Track Line at Y = 305)
        if (train.current_edge_id?.includes('DR') || train.current_location === 'DR') rawX = 440;
        else if (train.current_edge_id?.includes('CLA') || train.current_location === 'CLA') rawX = 605;
        else if (train.current_edge_id?.includes('PR') || train.current_location === 'PR') rawX = 385;
        else if (train.current_edge_id?.includes('GC') || train.current_location === 'GC') rawX = 715;
        else if (train.current_edge_id?.includes('TNA') || train.current_location === 'TNA') rawX = 1045;
        else if (train.current_edge_id?.includes('CSMT') || train.current_location === 'CSMT') rawX = 85;
        else rawX = nodePosMap[train.current_location] ?? 605;
      } else {
        const activeRoute = (train.route && train.route.length > 0)
          ? train.route
          : (isFast ? FAST_STOPS : FULL_CORRIDOR_ROUTE);

        const currLoc = train.current_location || 'CSMT';
        const currIdx = activeRoute.indexOf(currLoc);

        if (currIdx >= 0 && currIdx < activeRoute.length - 1) {
          const startX = nodePosMap[activeRoute[currIdx]] ?? 55;
          const endX = nodePosMap[activeRoute[currIdx + 1]] ?? (startX + 55);
          const prog = Math.min(100, Math.max(0, train.progress_percent || 0));
          rawX = startX + (endX - startX) * (prog / 100.0);
        } else {
          const locX = nodePosMap[currLoc];
          if (locX !== undefined) rawX = locX;
          else rawX = 55 + ((train.progress_percent || 0) / 100.0) * 990;
        }

        // Clamp Fast trains before blocked region (BY-DR blockage) - Keep train COMPLETELY STILL
        if (isTrackBlocked && isFast) {
          const byIdx = activeRoute.indexOf('BY') >= 0 ? activeRoute.indexOf('BY') : 1;
          const drIdx = activeRoute.indexOf('DR') >= 0 ? activeRoute.indexOf('DR') : 2;
          const safeStopX = nodePosMap['BY'] ?? 220;

          const isBlockedSection = train.current_edge_id?.includes('BY') || train.current_edge_id?.includes('DR') || train.status === 'Conflict' || currLoc === 'BY' || (currIdx >= 0 && currIdx <= byIdx && rawX >= safeStopX);
          const isNotPastBlock = currIdx < drIdx || (currIdx === drIdx && (train.progress_percent || 0) === 0);

          if (isBlockedSection && isNotPastBlock) {
            rawX = safeStopX; // Lock completely still at Byculla (X = 220) before Dadar blockage
          }
        }
      }

      return {
        ...train,
        rawX: Math.max(45, Math.min(1065, rawX)),
        y,
        isFast,
        isLoop,
      };
    });

    // 2. Anti-Collision Headway Enforcement (Separately on Track 1 Slow and Track 2 Fast)
    const MIN_HEADWAY_GAP = 54; // Minimum distance between train pill centers (badge is 48px wide)

    const slowGroup = rawList.filter((t) => !t.isFast && !t.isLoop).sort((a, b) => a.rawX - b.rawX);
    const fastGroup = rawList.filter((t) => t.isFast && !t.isLoop).sort((a, b) => a.rawX - b.rawX);
    const loopGroup = rawList.filter((t) => t.isLoop);

    const spaceGroup = (group: typeof rawList) => {
      if (group.length <= 1) return group.map((t) => ({ ...t, x: t.rawX }));
      const result = [...group];
      
      // Forward spacing pass
      for (let i = 1; i < result.length; i++) {
        if (result[i].rawX - result[i - 1].rawX < MIN_HEADWAY_GAP) {
          result[i].rawX = result[i - 1].rawX + MIN_HEADWAY_GAP;
        }
      }

      // Backward adjustment if right edge exceeds corridor boundary
      if (result[result.length - 1].rawX > 1055) {
        result[result.length - 1].rawX = 1055;
        for (let i = result.length - 2; i >= 0; i--) {
          if (result[i + 1].rawX - result[i].rawX < MIN_HEADWAY_GAP) {
            result[i].rawX = result[i + 1].rawX - MIN_HEADWAY_GAP;
          }
        }
      }

      return result.map((t) => ({ ...t, x: Math.max(45, Math.min(1060, t.rawX)) }));
    };

    const spacedSlow = spaceGroup(slowGroup);
    const spacedFast = spaceGroup(fastGroup);
    const spacedLoop = loopGroup.map((t) => ({ ...t, x: t.rawX }));

    return [...spacedSlow, ...spacedFast, ...spacedLoop];
  };

  const positionedTrains = getPositionedTrains();

  // Filter stations based on toggle
  const displayedStations = CORRIDOR_STATIONS.filter((s) => {
    if (filterMode === 'FAST') return s.isFast;
    if (filterMode === 'SLOW') return !s.isFast && s.isSlow;
    if (filterMode === 'LOOP') return s.hasLoop;
    return true;
  });

  return (
    <div className="w-full space-y-4 p-5 rounded-2xl bg-slate-900/95 border border-slate-800/90 shadow-2xl relative overflow-hidden">
      {/* Background Ambient Glows */}
      <div className="absolute top-0 right-0 w-[450px] h-[450px] bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-[450px] h-[450px] bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* Network Header */}
      <div className="border-b border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2">
                Live Railway Section Graph & Interlocking Map
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
                  Full 19-Station Central Corridor (CSMT ↔ Thane)
                </span>
              </h2>
              <p className="text-xs text-slate-400 font-medium">
                Dual Fast/Slow Lines + Loop Sidings • Individual Station Topologies & Real-Time Block Occupancy
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Station Filter Buttons */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setFilterMode('ALL')}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                filterMode === 'ALL' ? 'bg-slate-800 text-slate-100 font-bold shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All 19 Stations
            </button>
            <button
              onClick={() => setFilterMode('FAST')}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                filterMode === 'FAST' ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800/60 shadow' : 'text-slate-400 hover:text-cyan-400'
              }`}
            >
              Fast Halts (7)
            </button>
            <button
              onClick={() => setFilterMode('SLOW')}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                filterMode === 'SLOW' ? 'bg-emerald-950 text-emerald-300 font-bold border border-emerald-800/60 shadow' : 'text-slate-400 hover:text-emerald-400'
              }`}
            >
              Slow-Only (11)
            </button>
            <button
              onClick={() => setFilterMode('LOOP')}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                filterMode === 'LOOP' ? 'bg-amber-950 text-amber-300 font-bold border border-amber-800/60 shadow' : 'text-slate-400 hover:text-amber-400'
              }`}
            >
              Loop Sidings (5)
            </button>
          </div>

          <button
            onClick={() => setShowStationLegend(!showStationLegend)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition ${
              showStationLegend ? 'bg-slate-800 text-cyan-300 border-cyan-700/60' : 'bg-slate-950 text-slate-400 border-slate-800'
            }`}
          >
            <Info className="w-3.5 h-3.5" />
            <span>Station Legend (19)</span>
          </button>

          {isTrackBlocked && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/20 border border-rose-500/50 text-rose-300 text-xs font-bold animate-pulse shadow-lg">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>BY-DR FAST LINE BLOCKED</span>
            </div>
          )}

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
            <span>Interlocking: Active</span>
          </div>
        </div>
      </div>

      {/* Top Track Architecture Legend Bar (Clean, Non-Overlapping) */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-950/90 border border-slate-800 text-xs">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="w-4 h-2 rounded bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
            <span className="text-emerald-300 font-bold">Track 1 (Down Slow)</span>
            <span className="text-[10px] text-slate-500">• All 19 Stations Halt</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-2 rounded bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)]"></span>
            <span className="text-cyan-300 font-bold">Track 2 (Down Fast)</span>
            <span className="text-[10px] text-slate-500">• 7 Major Halts (CSMT, BY, DR, CLA, GC, MLND, TNA)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-2 rounded bg-amber-400 border border-dashed border-amber-300 shadow-[0_0_8px_rgba(245,158,11,0.5)]"></span>
            <span className="text-amber-300 font-bold">Loop Lines & Sidings</span>
            <span className="text-[10px] text-slate-500">• Dadar, Kurla, Ghatkopar, Thane, Parel</span>
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-400">
          Corridor Length: <span className="font-bold text-slate-200">32.7 km</span> • Single Direction: <span className="font-bold text-emerald-400">DOWN (Northbound)</span>
        </div>
      </div>

      {/* Collapsible 19-Station Code Legend */}
      {showStationLegend && (
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-[11px] font-mono text-slate-300 space-y-1.5 animate-fadeIn">
          <div className="text-xs font-bold text-cyan-300 flex items-center justify-between border-b border-slate-800/80 pb-1">
            <span>Mumbai Suburban Central Line — 19 Station Code Directory:</span>
            <span className="text-[10px] text-slate-400 font-normal">Blue Badge = Fast Halt • Green Badge = Slow Only</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-2 pt-1 text-[10.5px]">
            {CORRIDOR_STATIONS.map((s) => (
              <div
                key={s.code}
                className={`p-1.5 rounded-lg border flex items-center gap-1.5 ${
                  s.isFast
                    ? 'bg-cyan-950/40 border-cyan-800/50 text-cyan-200'
                    : 'bg-slate-900/60 border-slate-800 text-slate-300'
                }`}
              >
                <span className={`px-1.5 py-0.5 rounded font-extrabold text-[10px] ${s.isFast ? 'bg-cyan-500 text-slate-950' : 'bg-slate-800 text-slate-300'}`}>
                  {s.code}
                </span>
                <span className="truncate" title={s.name}>{s.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SVG Map Container */}
      <div className="relative w-full overflow-x-auto bg-slate-950 rounded-xl border border-slate-800 p-4 shadow-inner">
        <svg viewBox="0 0 1120 400" className="w-full h-auto min-w-[1040px]">
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.6" opacity="0.4" />
            </pattern>
            <pattern id="hatchBlocked" width="12" height="12" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="12" stroke="#ef4444" strokeWidth="3.5" opacity="0.85" />
            </pattern>
            <linearGradient id="fastTrackGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="50%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
            <linearGradient id="slowTrackGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
            <filter id="glowCyan" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="glowAmber" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Background Grid */}
          <rect width="1120" height="400" fill="url(#gridPattern)" />

          {/* Station Vertical Marker Beams & Labels */}
          {CORRIDOR_STATIONS.map((stn) => {
            const isHighlighted = displayedStations.some((s) => s.code === stn.code);
            return (
              <g
                key={stn.code}
                className="cursor-pointer group"
                onMouseEnter={() => setHoveredStation(stn)}
                onMouseLeave={() => setHoveredStation(null)}
              >
                {/* Vertical Guidelines */}
                <line
                  x1={stn.posX}
                  y1={45}
                  x2={stn.posX}
                  y2={355}
                  stroke={stn.isFast ? '#334155' : '#1e293b'}
                  strokeWidth={stn.isFast ? '1.5' : '1'}
                  strokeDasharray={stn.isFast ? '4 3' : '2 4'}
                  opacity={isHighlighted ? 0.9 : 0.25}
                />

                {/* Station Code Header */}
                <rect
                  x={stn.posX - 22}
                  y={18}
                  width="44"
                  height="22"
                  rx="6"
                  fill={stn.isFast ? '#083344' : '#020617'}
                  stroke={stn.isFast ? '#06b6d4' : '#475569'}
                  strokeWidth={stn.isFast ? '1.5' : '1'}
                  opacity={isHighlighted ? 1 : 0.3}
                />
                <text
                  x={stn.posX}
                  y={33}
                  textAnchor="middle"
                  fill={stn.isFast ? '#38bdf8' : '#cbd5e1'}
                  fontSize="10.5"
                  fontWeight="800"
                  fontFamily="monospace"
                >
                  {stn.code}
                </text>

                {/* Station KM Distance */}
                <text
                  x={stn.posX}
                  y={370}
                  textAnchor="middle"
                  fill="#64748b"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {stn.km}km
                </text>
              </g>
            );
          })}

          {/* ========================================================================= */}
          {/* 1. TRACK 1: SLOW LINE (Y = 125) - All 19 Stations Stop */}
          {/* ========================================================================= */}
          <g>
            {/* Track Bed Base */}
            <rect x="40" y="121" width="1025" height="8" fill="#0f172a" rx="4" />
            <line x1="45" y1="125" x2="1060" y2="125" stroke="url(#slowTrackGradient)" strokeWidth="4.5" strokeLinecap="round" />

            {/* Track Sleeper Ties */}
            {Array.from({ length: 70 }).map((_, i) => (
              <line
                key={`tie-slow-${i}`}
                x1={50 + i * 14.5}
                y1={120}
                x2={50 + i * 14.5}
                y2={130}
                stroke="#1e293b"
                strokeWidth="1.5"
              />
            ))}

            {/* Track Label Badge */}
            <rect x="5" y="113" width="46" height="24" rx="6" fill="#064e3b" stroke="#10b981" strokeWidth="1.5" />
            <text x="28" y="125" textAnchor="middle" fill="#ecfdf5" fontSize="8" fontWeight="900" fontFamily="monospace">
              TRACK 1
            </text>
            <text x="28" y="133" textAnchor="middle" fill="#a7f3d0" fontSize="7" fontWeight="bold" fontFamily="monospace">
              (SLOW)
            </text>
          </g>

          {/* ========================================================================= */}
          {/* 2. TRACK 2: FAST LINE (Y = 215) - Stops ONLY at 7 Fast Stations */}
          {/* ========================================================================= */}
          <g>
            {/* Track Bed Base */}
            <rect x="40" y="211" width="1025" height="8" fill="#0f172a" rx="4" />
            <line
              x1="45"
              y1="215"
              x2="1060"
              y2="215"
              stroke="url(#fastTrackGradient)"
              strokeWidth="5"
              strokeLinecap="round"
              filter="url(#glowCyan)"
            />

            {/* Track Label Badge */}
            <rect x="5" y="203" width="46" height="24" rx="6" fill="#083344" stroke="#06b6d4" strokeWidth="1.5" />
            <text x="28" y="215" textAnchor="middle" fill="#ecfeff" fontSize="8" fontWeight="900" fontFamily="monospace">
              TRACK 2
            </text>
            <text x="28" y="223" textAnchor="middle" fill="#67e8f9" fontSize="7" fontWeight="bold" fontFamily="monospace">
              (FAST)
            </text>

            {/* Fast Line Skip Indicators over Slow-Only stations */}
            {CORRIDOR_STATIONS.filter((s) => !s.isFast).map((stn) => (
              <g key={`skip-${stn.code}`}>
                <rect x={stn.posX - 10} y="210" width="20" height="10" fill="#020617" rx="3" stroke="#334155" strokeWidth="1" />
                <path d={`M ${stn.posX - 5} 215 L ${stn.posX} 212 L ${stn.posX + 5} 215`} fill="none" stroke="#64748b" strokeWidth="1.5" />
                <text x={stn.posX} y="232" textAnchor="middle" fill="#64748b" fontSize="7.5" fontWeight="bold" fontFamily="monospace">
                  SKIP
                </text>
              </g>
            ))}
          </g>

          {/* ========================================================================= */}
          {/* ========================================================================= */}
          {/* 3. TRACK 3 & LOOP LINES (Y = 305) - Full Corridor Sidings & Interlocking Loops */}
          {/* ========================================================================= */}
          <g>
            {/* Loop Header Badge */}
            <g
              className="cursor-pointer group"
              onMouseEnter={() => setShowLoopInfo(true)}
              onMouseLeave={() => setShowLoopInfo(false)}
              onClick={() => setShowLoopInfo(!showLoopInfo)}
            >
              <rect x="5" y="293" width="46" height="24" rx="6" fill="#451a03" stroke="#f59e0b" strokeWidth="1.5" />
              <text x="28" y="305" textAnchor="middle" fill="#fffbeb" fontSize="8" fontWeight="900" fontFamily="monospace">
                LOOP
              </text>
              <text x="28" y="313" textAnchor="middle" fill="#fde68a" fontSize="7" fontWeight="bold" fontFamily="monospace">
                SIDINGS
              </text>
            </g>

            {/* Continuous Track 3 Loop Bed Base & Rails (Spans entire corridor from CSMT to Thane) */}
            <rect x="40" y="301" width="1025" height="8" fill="#0f172a" rx="4" />
            <line
              x1="45"
              y1="305"
              x2="1060"
              y2="305"
              stroke="#d97706"
              strokeWidth="4"
              strokeLinecap="round"
            />
            {/* Loop Track Sleeper Ties across whole corridor */}
            {Array.from({ length: 70 }).map((_, i) => (
              <line
                key={`tie-loop-${i}`}
                x1={50 + i * 14.5}
                y1={300}
                x2={50 + i * 14.5}
                y2={310}
                stroke="#1e293b"
                strokeWidth="1.5"
              />
            ))}

            {/* A. CSMT Goods Yard Siding (X = 55-100) */}
            <path d="M 55 215 Q 70 305 85 305" fill="none" stroke="#f59e0b" strokeWidth="2.5" />
            <rect x="68" y="298" width="42" height="14" rx="4" fill="#0f172a" stroke="#f59e0b" strokeWidth="1.5" />
            <text x="89" y="308" textAnchor="middle" fill="#fde047" fontSize="7" fontWeight="extrabold">CSMT YARD</text>

            {/* B. Parel Siding (PR: X=360-410) */}
            <path d="M 360 215 Q 375 305 385 305 L 410 305" fill="none" stroke="#f59e0b" strokeWidth="2.5" />
            <rect x="370" y="298" width="40" height="14" rx="4" fill="#0f172a" stroke="#f59e0b" strokeWidth="1.5" />
            <text x="390" y="308" textAnchor="middle" fill="#fde047" fontSize="7" fontWeight="extrabold">PR SIDING</text>

            {/* C. Dadar Interlocking Loop (DR: X=410-480) */}
            <path
              d="M 410 215 Q 425 305 440 305 L 465 305 Q 480 305 495 215"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="3"
              filter="url(#glowAmber)"
            />
            <path d="M 440 305 Q 450 125 465 125" fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="4 2" />
            <rect x="425" y="298" width="38" height="14" rx="4" fill="#0f172a" stroke="#f59e0b" strokeWidth="1.5" />
            <text x="444" y="308" textAnchor="middle" fill="#fde047" fontSize="7.5" fontWeight="extrabold">DR LOOP</text>

            {/* D. Kurla Car Shed / Goods Loop (CLA: X=575-645) */}
            <path
              d="M 575 215 Q 590 305 605 305 L 630 305 Q 645 305 660 215"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="3"
              filter="url(#glowAmber)"
            />
            <path d="M 605 305 Q 615 125 630 125" fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="4 2" />
            <rect x="590" y="298" width="40" height="14" rx="4" fill="#0f172a" stroke="#f59e0b" strokeWidth="1.5" />
            <text x="610" y="308" textAnchor="middle" fill="#fde047" fontSize="7.5" fontWeight="extrabold">CLA LOOP</text>

            {/* E. Ghatkopar Metro Interchange Loop (GC: X=685-755) */}
            <path
              d="M 685 215 Q 700 305 715 305 L 740 305 Q 755 305 770 215"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="3"
              filter="url(#glowAmber)"
            />
            <rect x="700" y="298" width="38" height="14" rx="4" fill="#0f172a" stroke="#f59e0b" strokeWidth="1.5" />
            <text x="719" y="308" textAnchor="middle" fill="#fde047" fontSize="7.5" fontWeight="extrabold">GC LOOP</text>

            {/* F. Thane Major Terminus Loops (TNA: X=1010-1070) */}
            <path
              d="M 1010 215 Q 1025 305 1045 305 L 1065 305"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="3"
              filter="url(#glowAmber)"
            />
            <rect x="1030" y="298" width="36" height="14" rx="4" fill="#0f172a" stroke="#f59e0b" strokeWidth="1.5" />
            <text x="1048" y="308" textAnchor="middle" fill="#fde047" fontSize="7.5" fontWeight="extrabold">TNA YARD</text>
          </g>

          {/* Crossover Link at Byculla (BY: X=220) between Fast and Slow lines */}
          <path d="M 220 215 Q 235 125 250 125" fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeDasharray="4 2" />
          <text x="248" y="172" fill="#38bdf8" fontSize="7.5" fontWeight="bold" fontFamily="monospace">
            Switch S-14
          </text>

          {/* ========================================================================= */}
          {/* TRACK BLOCKAGE VISUALIZER (When BY_DR is Blocked) */}
          {/* ========================================================================= */}
          {isTrackBlocked && (
            <g>
              <rect x="235" y="200" width="200" height="30" fill="url(#hatchBlocked)" rx="6" opacity="0.9" />
              <rect x="235" y="200" width="200" height="30" fill="none" stroke="#ef4444" strokeWidth="2.5" rx="6" />
              <rect x="250" y="207" width="170" height="16" rx="4" fill="#450a0a" stroke="#ef4444" strokeWidth="1" />
              <text x="335" y="219" textAnchor="middle" fill="#fee2e2" fontSize="9" fontWeight="900" fontFamily="monospace">
                ⛔ BY-DR FAST TRACK BLOCKED
              </text>
            </g>
          )}

          {/* ========================================================================= */}
          {/* 4. STATION PLATFORM NODES (Distinct Slow vs Fast Halts) */}
          {/* ========================================================================= */}
          {CORRIDOR_STATIONS.map((stn) => {
            const isHighlighted = displayedStations.some((s) => s.code === stn.code);
            return (
              <g
                key={`platform-nodes-${stn.code}`}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredStation(stn)}
                onMouseLeave={() => setHoveredStation(null)}
              >
                {/* Slow Line Platform Halt Node (At All 19 Stations) */}
                <circle
                  cx={stn.posX}
                  cy="125"
                  r="7"
                  fill="#020617"
                  stroke={isHighlighted ? '#10b981' : '#334155'}
                  strokeWidth="2.5"
                />
                <circle cx={stn.posX} cy="125" r="3" fill={isHighlighted ? '#10b981' : '#64748b'} />

                {/* Fast Line Platform Node (ONLY at Fast Stations) */}
                {stn.isFast ? (
                  <g>
                    {/* Fast Interchange Diamond Node */}
                    <polygon
                      points={`${stn.posX},205 ${stn.posX + 10},215 ${stn.posX},225 ${stn.posX - 10},215`}
                      fill="#020617"
                      stroke={isHighlighted ? '#06b6d4' : '#334155'}
                      strokeWidth="2.5"
                    />
                    <circle cx={stn.posX} cy="215" r="3.5" fill="#38bdf8" />
                    {/* Fast Station Badge */}
                    <rect x={stn.posX - 14} y="238" width="28" height="13" rx="3" fill="#083344" stroke="#06b6d4" strokeWidth="1" />
                    <text x={stn.posX} y="248" textAnchor="middle" fill="#67e8f9" fontSize="7.5" fontWeight="extrabold" fontFamily="monospace">
                      FAST
                    </text>
                  </g>
                ) : (
                  // Slow Only Station Badge
                  <g>
                    <rect x={stn.posX - 13} y="137" width="26" height="12" rx="3" fill="#064e3b" stroke="#10b981" strokeWidth="1" />
                    <text x={stn.posX} y="146" textAnchor="middle" fill="#a7f3d0" fontSize="7" fontWeight="bold" fontFamily="monospace">
                      SLOW
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* ========================================================================= */}
          {/* 5. MOVING TRAIN MARKERS ON ALL TRACKS (Collision-Free Safety Spaced) */}
          {/* ========================================================================= */}
          {positionedTrains.map((train) => {
            const trainX = train.x;
            const trainY = train.y;
            const statusColor = getStatusColor(train.status);
            const isSelected = selectedTrainId === train.id;

            return (
              <g
                key={train.id}
                className="cursor-pointer group"
                onClick={() => onSelectTrain(train)}
                onMouseEnter={() => setHoveredTrain(train)}
                onMouseLeave={() => setHoveredTrain(null)}
              >
                {/* Selection Ring */}
                {isSelected && (
                  <circle cx={trainX} cy={trainY} r="20" fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeDasharray="3 3">
                    <animateTransform
                      attributeName="transform"
                      type="rotate"
                      from={`0 ${trainX} ${trainY}`}
                      to={`360 ${trainX} ${trainY}`}
                      dur="6s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}

                {/* Train Marker Badge */}
                <rect
                  x={trainX - 24}
                  y={trainY - 13}
                  width="48"
                  height="26"
                  rx="13"
                  fill="#020617"
                  stroke={statusColor}
                  strokeWidth="2.5"
                  className="group-hover:stroke-white transition shadow-lg"
                />

                {/* Train ID Text */}
                <text
                  x={trainX}
                  y={trainY + 4}
                  textAnchor="middle"
                  fill="#f8fafc"
                  fontSize="10"
                  fontWeight="900"
                  fontFamily="monospace"
                >
                  {train.id}
                </text>

                {/* Pulsing Status Dot */}
                <circle cx={trainX + 17} cy={trainY - 7} r="3" fill={statusColor} />
              </g>
            );
          })}
        </svg>

        {/* Hovered Train Tooltip */}
        {hoveredTrain && (
          <div className="absolute top-4 right-4 p-4 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl text-xs space-y-1.5 backdrop-blur pointer-events-none z-20 font-mono min-w-[280px]">
            <div className="flex items-center justify-between font-bold text-slate-100 border-b border-slate-800 pb-1.5 gap-4">
              <span className="text-sm font-bold text-white">{hoveredTrain.name}</span>
              <span className="text-cyan-400 font-extrabold">({hoveredTrain.id})</span>
            </div>
            <div className="text-slate-300">
              Type: <span className="font-semibold text-slate-100">{hoveredTrain.type}</span> | Priority:{' '}
              <span className={hoveredTrain.priority === 'High' ? 'text-rose-400 font-bold' : 'text-slate-200'}>{hoveredTrain.priority}</span>
            </div>
            <div className="text-slate-300">
              Location: <span className="font-semibold text-slate-100">{hoveredTrain.current_location_name}</span> | Speed:{' '}
              <span className="font-bold text-emerald-400">{hoveredTrain.speed_kmh} km/h</span>
            </div>
            <div className="text-slate-400">
              Track: <span className="text-cyan-300 font-semibold">{hoveredTrain.assigned_track}</span>
            </div>
            <div className="flex items-center justify-between text-slate-400 pt-1 border-t border-slate-800">
              <span>Delay: <span className="text-amber-400 font-bold">{hoveredTrain.delay_min} min</span></span>
              <span>Progress: <span className="text-emerald-400 font-bold">{hoveredTrain.progress_percent}%</span></span>
            </div>
          </div>
        )}

        {/* Hovered Station Info Tooltip */}
        {hoveredStation && !hoveredTrain && (
          <div className="absolute top-4 right-4 p-4 rounded-xl bg-slate-900/95 border border-cyan-500/40 shadow-2xl text-xs space-y-2 backdrop-blur pointer-events-none z-20 min-w-[320px]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
              <div>
                <span className="text-base font-extrabold text-white">{hoveredStation.name}</span>
                <span className="text-cyan-400 font-mono font-bold ml-2">[{hoveredStation.code}]</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 font-bold">
                {hoveredStation.km} km
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-slate-300">
              <div>
                <span className="text-slate-500 text-[11px] block">Station Type:</span>
                <span className="font-bold text-slate-100">{hoveredStation.type}</span>
              </div>
              <div>
                <span className="text-slate-500 text-[11px] block">Platforms:</span>
                <span className="font-bold text-emerald-400">{hoveredStation.pf}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${hoveredStation.isFast ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-slate-800 text-slate-500'}`}>
                {hoveredStation.isFast ? '✓ Fast Line Halt' : '✕ Fast Trains Skip'}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                ✓ Slow Line Halt
              </span>
              {hoveredStation.hasLoop && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800">
                  ★ Loop Siding
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed border-t border-slate-800 pt-1.5">
              <span className="text-slate-300 font-semibold">Infrastructure: </span>{hoveredStation.infra}
            </p>
          </div>
        )}

        {/* Loop Track Explanation Tooltip / Popover */}
        {showLoopInfo && (
          <div className="absolute bottom-4 left-4 max-w-sm p-4 rounded-xl bg-slate-900/95 border border-amber-500/50 shadow-2xl text-xs space-y-2 backdrop-blur z-30 font-sans">
            <div className="flex items-center justify-between font-bold text-amber-400 border-b border-slate-800 pb-1.5">
              <div className="flex items-center gap-1.5">
                <Info className="w-4 h-4 text-amber-400" />
                <span>Loop Track & Siding Architecture</span>
              </div>
              <button
                onClick={() => setShowLoopInfo(false)}
                className="text-slate-400 hover:text-white text-xs px-1.5 py-0.5 rounded bg-slate-800"
              >
                ✕
              </button>
            </div>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              A loop track is an auxiliary directional siding branching off the main running line (via turnout points). It allows local EMU trains or slower traffic to be safely looped/berthered while higher-priority Superfast / Vande Bharat Expresses overtake without congestion.
            </p>
            <div className="text-[11px] text-amber-300 font-mono bg-amber-950/40 p-2 rounded border border-amber-800/40">
              Active Loop Sidings: Dadar (DR), Kurla (CLA), Ghatkopar (GC), Thane (TNA), Parel (PR)
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveRailwayNetwork;
