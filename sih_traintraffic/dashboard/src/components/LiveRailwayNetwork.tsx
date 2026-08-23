import React, { useState } from 'react';
import type { StationNode, Train } from '../types/railway';
import { Layers, Info } from 'lucide-react';

interface LiveRailwayNetworkProps {
  nodes: StationNode[];
  trains: Train[];
  onSelectTrain: (train: Train) => void;
  selectedTrainId?: string;
}

export const LiveRailwayNetwork: React.FC<LiveRailwayNetworkProps> = ({
  nodes,
  trains,
  onSelectTrain,
  selectedTrainId,
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
        return '#f97316'; // Orange
      default:
        return '#10b981';
    }
  };

  return (
    <div className="w-full space-y-4 p-5 rounded-xl bg-slate-900/90 border border-slate-800/90 shadow-2xl relative overflow-hidden">
      {/* Glow Effect */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* Network Header */}
      <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg sm:text-xl font-bold text-slate-100 tracking-tight">Live Railway Section Graph</h2>
          </div>
          <p className="text-xs text-slate-400 font-medium">
            Mumbai Central Line Corridor • Multi-Track Interlocking & Real-Time Block Occupancy
          </p>
        </div>

        <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          <span>Dual-Track Active</span>
        </div>
      </div>

      {/* SVG Map Container */}
      <div className="relative w-full overflow-x-auto bg-slate-950/95 rounded-xl border border-slate-800/80 p-4 shadow-inner">
        {/* Status Key Overlay Top-Left */}
        <div className="absolute top-4 left-4 z-10 text-xs space-y-1.5 text-slate-400 font-medium pointer-events-none bg-slate-950/80 p-3 rounded-lg border border-slate-800/60 backdrop-blur">
          <div className="text-slate-200 font-bold mb-1 border-b border-slate-800 pb-1">Status Key</div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shadow-sm"></span>
            <span className="text-slate-300">Moving</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block shadow-sm"></span>
            <span className="text-slate-300">Waiting</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block shadow-sm"></span>
            <span className="text-slate-300">Delayed</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block shadow-sm"></span>
            <span className="text-slate-300">Conflict/Risk</span>
          </div>
        </div>

        <svg viewBox="0 0 1000 320" className="w-full h-auto min-w-[850px]">
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.5" opacity="0.3" />
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
              {/* Station Code Label Top */}
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
          {/* 1. SLOW LINE (Dashed Gray) */}
          <text x="50" y="155" fill="#94a3b8" fontSize="11" fontWeight="bold" fontFamily="monospace">
            SLOW LINE
          </text>
          <line x1="120" y1="150" x2="900" y2="150" stroke="#475569" strokeWidth="3" strokeDasharray="8 4" />

          {/* 2. FAST LINE (Solid Cyan) */}
          <text x="50" y="225" fill="#06b6d4" fontSize="11" fontWeight="bold" fontFamily="monospace">
            FAST LINE
          </text>
          <line x1="120" y1="220" x2="900" y2="220" stroke="#06b6d4" strokeWidth="4" filter="url(#glowCyan)" />

          {/* 3. Loop / Crossover Lines (Orange Dashed Curve) */}
          <path
            d="M 360 220 Q 400 280 440 220 M 540 220 Q 580 280 620 220"
            fill="none"
            stroke="#f59e0b"
            strokeWidth="2.5"
            strokeDasharray="4 2"
          />

          {/* Station Node Circles */}
          {nodes.map((node) => (
            <g key={`node-circle-${node.station_code}`}>
              {/* SLOW LINE Station Node */}
              <circle
                cx={node.pos_x}
                cy="150"
                r="6"
                fill="#0f172a"
                stroke="#10b981"
                strokeWidth="3"
              />

              {/* FAST LINE Station Target Ring */}
              <circle
                cx={node.pos_x}
                cy="220"
                r="10"
                fill="#0f172a"
                stroke="#06b6d4"
                strokeWidth="3"
              />
              <circle
                cx={node.pos_x}
                cy="220"
                r="4"
                fill="#06b6d4"
              />
            </g>
          ))}

          {/* MOVING TRAIN MARKERS */}
          {trains.map((train) => {
            const trainX = 60 + (train.progress_percent / 100) * 840;
            const isFast = train.assigned_track.includes('FAST');
            const isLoop = train.assigned_track.includes('Loop');
            const trainY = isLoop ? 260 : isFast ? 220 : 150;
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
                {/* Selection Pulse Ring */}
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

                {/* Train Badge Pill */}
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

        {/* Hovered Train Tooltip Card */}
        {hoveredTrain && (
          <div className="absolute top-4 right-4 p-3 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl text-xs space-y-1 backdrop-blur pointer-events-none z-20">
            <div className="flex items-center justify-between font-bold text-slate-100 gap-4">
              <span>{hoveredTrain.name}</span>
              <span className="font-mono text-cyan-400">({hoveredTrain.id})</span>
            </div>
            <div className="text-[11px] text-slate-300">
              Loc: <span className="font-semibold text-slate-100">{hoveredTrain.current_location_name}</span> | Speed:{' '}
              <span className="font-mono font-bold text-emerald-400">{hoveredTrain.speed_kmh} km/h</span>
            </div>
            <div className="text-[11px] text-slate-400">
              Track: <span className="font-mono text-cyan-300">{hoveredTrain.assigned_track}</span> | Delay:{' '}
              <span className="font-mono text-amber-400">{hoveredTrain.delay_min} min</span>
            </div>
          </div>
        )}
      </div>

      {/* Helper Footer */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>Click any train marker (T101, T104, T218, T201) to inspect real-time telemetry, delay predictions, and route details.</span>
        </div>
      </div>
    </div>
  );
};
