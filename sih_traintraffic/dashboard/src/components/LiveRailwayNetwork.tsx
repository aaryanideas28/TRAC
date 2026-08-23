import React, { useState } from 'react';
import type { StationNode, Train } from '../types/railway';
import { Layers, AlertTriangle } from 'lucide-react';

interface LiveRailwayNetworkProps {
  nodes: StationNode[];
  trains: Train[];
  onSelectTrain: (train: Train) => void;
  selectedTrainId?: string;
  isTrackBlocked?: boolean;
}

export const LiveRailwayNetwork: React.FC<LiveRailwayNetworkProps> = ({
  nodes,
  trains,
  onSelectTrain,
  selectedTrainId,
  isTrackBlocked = false,
}) => {
  const [hoveredTrain, setHoveredTrain] = useState<Train | null>(null);

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

  // Node position lookup map
  const nodePosMap: Record<string, number> = {
    CSMT: 60,
    BY: 220,
    DR: 400,
    CLA: 580,
    GC: 740,
    TNA: 900,
  };

  // Compute interpolated train X coordinate along graph edge
  const getTrainX = (train: Train): number => {
    const route = train.route && train.route.length > 0 ? train.route : ['CSMT', 'BY', 'DR', 'CLA', 'GC', 'TNA'];
    const currLoc = train.current_location || 'CSMT';
    const currIdx = route.indexOf(currLoc);

    if (currIdx >= 0 && currIdx < route.length - 1) {
      const startX = nodePosMap[route[currIdx]] ?? 60;
      const endX = nodePosMap[route[currIdx + 1]] ?? (startX + 160);
      const prog = Math.min(100, Math.max(0, train.progress_percent || 0));
      return startX + (endX - startX) * (prog / 100.0);
    }

    const locX = nodePosMap[currLoc];
    if (locX !== undefined) return locX;
    return 60 + ((train.progress_percent || 0) / 100.0) * 840;
  };

  return (
    <div className="w-full space-y-4 p-5 rounded-2xl bg-slate-900/90 border border-slate-800/90 shadow-2xl relative overflow-hidden">
      {/* Glow Effect */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* Network Header */}
      <div className="border-b border-slate-800 pb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg sm:text-xl font-extrabold text-slate-100 tracking-tight">
              Live Railway Section Graph & Interlocking Map
            </h2>
          </div>
          <p className="text-xs text-slate-400 font-medium">
            Mumbai Central Line Corridor • Continuous Real-Time Edge Positions & Track Block Occupancy
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isTrackBlocked && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 text-xs font-bold animate-pulse">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span>BY_DR SECTION BLOCKED</span>
            </div>
          )}
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span>Live Interlocking Active</span>
          </div>
        </div>
      </div>

      {/* SVG Map Container */}
      <div className="relative w-full overflow-x-auto bg-slate-950/95 rounded-xl border border-slate-800/80 p-4 shadow-inner">
        {/* Status Key Overlay */}
        <div className="absolute top-4 left-4 z-10 text-[11px] space-y-1 text-slate-400 font-medium pointer-events-none bg-slate-950/80 p-3 rounded-lg border border-slate-800/60 backdrop-blur">
          <div className="text-slate-200 font-bold mb-1 border-b border-slate-800 pb-1">Status Key</div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shadow-sm"></span>
            <span className="text-slate-300">Moving (Green)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block shadow-sm"></span>
            <span className="text-slate-300">Waiting (Yellow)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block shadow-sm"></span>
            <span className="text-slate-300">Conflict / Blocked (Red)</span>
          </div>
        </div>

        <svg viewBox="0 0 1000 320" className="w-full h-auto min-w-[850px]">
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.5" opacity="0.3" />
            </pattern>
            <pattern id="hatchBlocked" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="10" stroke="#ef4444" strokeWidth="3" opacity="0.7" />
            </pattern>
            <filter id="glowCyan" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>
          <rect width="1000" height="320" fill="url(#gridPattern)" />

          {/* Station Vertical Marker Beams */}
          {nodes.map((node) => (
            <g key={node.station_code}>
              <line
                x1={node.pos_x}
                y1={40}
                x2={node.pos_x}
                y2={280}
                stroke="#334155"
                strokeWidth="1.5"
                strokeDasharray="3 3"
              />
              <text
                x={node.pos_x}
                y={30}
                textAnchor="middle"
                fill="#f8fafc"
                fontSize="13"
                fontWeight="800"
                fontFamily="monospace"
              >
                {node.station_code}
              </text>
            </g>
          ))}

          {/* MAIN TRACK LINES */}
          {/* 1. SLOW LINE (Track 1) */}
          <text x="50" y="145" fill="#94a3b8" fontSize="10" fontWeight="bold" fontFamily="monospace">
            TRACK 1 (SLOW)
          </text>
          <line x1="60" y1="150" x2="900" y2="150" stroke="#475569" strokeWidth="3.5" strokeDasharray="8 4" />

          {/* 2. FAST LINE (Track 2) */}
          <text x="50" y="215" fill="#06b6d4" fontSize="10" fontWeight="bold" fontFamily="monospace">
            TRACK 2 (FAST)
          </text>
          <line x1="60" y1="220" x2="900" y2="220" stroke="#06b6d4" strokeWidth="4" filter="url(#glowCyan)" />

          {/* 3. LOOP TRACK LINE (Track 4) */}
          <text x="50" y="265" fill="#f59e0b" fontSize="10" fontWeight="bold" fontFamily="monospace">
            LOOP TRACK
          </text>

          {/* Crossover curves */}
          <path
            d="M 360 220 Q 400 270 440 220 M 540 220 Q 580 270 620 220"
            fill="none"
            stroke="#f59e0b"
            strokeWidth="2.5"
            strokeDasharray="4 2"
          />

          {/* Track Blockage Highlight Box if BY_DR blocked */}
          {isTrackBlocked && (
            <g>
              <rect x="220" y="206" width="180" height="28" fill="url(#hatchBlocked)" rx="4" opacity="0.8" />
              <rect x="220" y="206" width="180" height="28" fill="none" stroke="#ef4444" strokeWidth="2" rx="4" />
              <text x="310" y="223" textAnchor="middle" fill="#fef2f2" fontSize="10" fontWeight="900" fontFamily="monospace">
                ⛔ TRACK BLOCKED (BY-DR)
              </text>
            </g>
          )}

          {/* Station Node Circles */}
          {nodes.map((node) => (
            <g key={`node-circle-${node.station_code}`}>
              {/* Slow Line Station Circle */}
              <circle cx={node.pos_x} cy="150" r="6" fill="#0f172a" stroke="#10b981" strokeWidth="2.5" />
              {/* Fast Line Station Circle */}
              <circle cx={node.pos_x} cy="220" r="8" fill="#0f172a" stroke="#06b6d4" strokeWidth="2.5" />
              <circle cx={node.pos_x} cy="220" r="3" fill="#06b6d4" />
            </g>
          ))}

          {/* MOVING TRAIN MARKERS */}
          {trains.map((train) => {
            const trainX = getTrainX(train);
            const isFast = train.assigned_track.includes('Fast');
            const isLoop = train.assigned_track.includes('Loop');
            const trainY = isLoop ? 270 : isFast ? 220 : 150;
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
                  <circle cx={trainX} cy={trainY} r="18" fill="none" stroke="#38bdf8" strokeWidth="2" strokeDasharray="3 3">
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
                  x={trainX - 22}
                  y={trainY - 12}
                  width="44"
                  height="24"
                  rx="12"
                  fill="#020617"
                  stroke={statusColor}
                  strokeWidth="2.5"
                />
                <text
                  x={trainX}
                  y={trainY + 4}
                  textAnchor="middle"
                  fill="#f8fafc"
                  fontSize="10"
                  fontWeight="extrabold"
                  fontFamily="monospace"
                >
                  {train.id}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hovered Train Tooltip */}
        {hoveredTrain && (
          <div className="absolute top-4 right-4 p-3 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl text-xs space-y-1 backdrop-blur pointer-events-none z-20 font-mono">
            <div className="flex items-center justify-between font-bold text-slate-100 gap-4">
              <span>{hoveredTrain.name}</span>
              <span className="text-cyan-400">({hoveredTrain.id})</span>
            </div>
            <div className="text-slate-300">
              Location: <span className="font-semibold text-slate-100">{hoveredTrain.current_location_name}</span> | Speed:{' '}
              <span className="font-bold text-emerald-400">{hoveredTrain.speed_kmh} km/h</span>
            </div>
            <div className="text-slate-400">
              Track: <span className="text-cyan-300">{hoveredTrain.assigned_track}</span> | Delay:{' '}
              <span className="text-amber-400">{hoveredTrain.delay_min} min</span> | Progress: {hoveredTrain.progress_percent}%
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
