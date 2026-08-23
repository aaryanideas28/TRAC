import { useState, useEffect, useCallback } from 'react';
import { apiService } from './services/apiService';
import type { StationNode, Train, AiRecommendation, ConflictItem, KpiMetrics, BeforeAfterMetrics, SimulationState } from './types/railway';
import { TopNav } from './components/TopNav';
import { KpiCards } from './components/KpiCards';
import { LiveRailwayNetwork } from './components/LiveRailwayNetwork';
import { BeforeAfterComparison } from './components/BeforeAfterComparison';
import { AiRecommendationPanel } from './components/AiRecommendationPanel';
import { ConflictMonitor } from './components/ConflictMonitor';
import { TrainScheduleTable } from './components/TrainScheduleTable';
import { AnalyticsView } from './components/AnalyticsView';
import { SimulationControl } from './components/SimulationControl';
import { MlVisualizationPanel } from './components/MlVisualizationPanel';
import { OrToolsVisualizationPanel } from './components/OrToolsVisualizationPanel';
import { LiveSystemEventLog } from './components/LiveSystemEventLog';
import { TrainDetailModal } from './components/TrainDetailModal';
import { DemoFlowGuide } from './components/DemoFlowGuide';
import { DataProvenancePanel } from './components/DataProvenancePanel';
import { PrototypeAssumptionsPanel } from './components/PrototypeAssumptionsPanel';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [simState, setSimState] = useState<SimulationState | null>(null);

  const [nodes, setNodes] = useState<StationNode[]>([]);
  const [trains, setTrains] = useState<Train[]>([]);
  const [recommendations, setRecommendations] = useState<AiRecommendation[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [metrics, setMetrics] = useState<KpiMetrics | null>(null);
  const [beforeAfter, setBeforeAfter] = useState<BeforeAfterMetrics | null>(null);

  const [selectedTrain, setSelectedTrain] = useState<Train | null>(null);
  const [systemStatus, setSystemStatus] = useState('CONNECTED');
  const [lastUpdated, setLastUpdated] = useState('');

  // Demo walkthrough state
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoStep, setDemoStep] = useState(0);

  // Load graph topology once on mount
  useEffect(() => {
    apiService.fetchNetwork().then((net) => setNodes(net.nodes)).catch(() => {});
  }, []);

  // Main 1-second simulation tick poll
  const pollSimulationState = useCallback(async () => {
    try {
      const state = await apiService.fetchSimulationState();
      setSimState(state);

      if (state.trains) setTrains(state.trains);
      if (state.metrics) setMetrics(state.metrics);
      if (state.before_after) setBeforeAfter(state.before_after);
      if (state.recommendations) setRecommendations(state.recommendations);
      if (state.conflicts) setConflicts(state.conflicts);

      setSystemStatus(state.backend_status);
      setLastUpdated(state.sim_time || new Date().toLocaleTimeString('en-US', { hour12: false }));
    } catch (e) {
      setSystemStatus('DISCONNECTED');
    }
  }, []);

  useEffect(() => {
    pollSimulationState();
    const interval = setInterval(pollSimulationState, 1000); // 1-second refresh rate
    return () => clearInterval(interval);
  }, [pollSimulationState]);

  const handleRunOptimization = async () => {
    const res = await apiService.runOptimization();
    if (res.simulation_state) {
      setSimState(res.simulation_state);
      setTrains(res.simulation_state.trains);
      setMetrics(res.simulation_state.metrics);
      setBeforeAfter(res.simulation_state.before_after);
      setRecommendations(res.simulation_state.recommendations);
      setConflicts(res.simulation_state.conflicts);
    }
    await pollSimulationState();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* Top Header */}
      <TopNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        simTime={simState?.sim_time || ''}
        tickCount={simState?.tick_count || 0}
        lastUpdated={lastUpdated}
        onRefresh={pollSimulationState}
        onStartDemo={() => {
          setIsDemoMode(true);
          setDemoStep(0);
          setActiveTab('dashboard');
        }}
      />

      {/* SIH Demo Flow Walkthrough Banner */}
      {isDemoMode && (
        <div className="w-full max-w-[1600px] mx-auto px-4 pt-4">
          <DemoFlowGuide
            currentStep={demoStep}
            setCurrentStep={setDemoStep}
            onClose={() => setIsDemoMode(false)}
            onSelectTab={(tab) => setActiveTab(tab)}
            onRunOptimization={handleRunOptimization}
          />
        </div>
      )}

      {/* Main Dashboard Layout Container */}
      <main className="w-full max-w-[1600px] mx-auto p-4 md:p-6 space-y-6">
        {/* Top Summary KPI Cards */}
        {metrics && <KpiCards metrics={metrics} lastUpdated={lastUpdated} />}

        {/* Incident Simulator Toolbar (SIH Judge Perturbation Controls) */}
        <SimulationControl
          simState={simState}
          onStateUpdate={(st) => setSimState(st)}
          onRunOptimization={handleRunOptimization}
        />

        {/* Dynamic Tab Views */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Live Interactive Railway Map */}
            <LiveRailwayNetwork
              nodes={nodes}
              trains={trains}
              onSelectTrain={(t) => setSelectedTrain(t)}
              selectedTrainId={selectedTrain?.id}
              isTrackBlocked={simState?.track_blocked}
            />

            {/* Intelligence Output panels: ML Prediction & OR-Tools Solver */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
              <MlVisualizationPanel mlPrediction={simState?.ml_prediction} />
              <OrToolsVisualizationPanel optimizationState={simState?.optimization_state} />
            </div>

            {/* Live System Event Log */}
            <LiveSystemEventLog events={simState?.event_logs} />

            {/* Side-by-Side BEFORE vs WITH AI */}
            {beforeAfter && <BeforeAfterComparison metrics={beforeAfter} />}

            {/* Split View: AI Recommendations & Live Conflict Radar */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
              <AiRecommendationPanel recommendations={recommendations} />
              <ConflictMonitor conflicts={conflicts} />
            </div>

            {/* Data Provenance & Assumptions (Judge Audit Accordions) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full pt-2">
              <DataProvenancePanel />
              <PrototypeAssumptionsPanel />
            </div>
          </div>
        )}

        {activeTab === 'network' && (
          <div className="space-y-6">
            <LiveRailwayNetwork
              nodes={nodes}
              trains={trains}
              onSelectTrain={(t) => setSelectedTrain(t)}
              selectedTrainId={selectedTrain?.id}
              isTrackBlocked={simState?.track_blocked}
            />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
              <MlVisualizationPanel mlPrediction={simState?.ml_prediction} />
              <OrToolsVisualizationPanel optimizationState={simState?.optimization_state} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
              <AiRecommendationPanel recommendations={recommendations} />
              <ConflictMonitor conflicts={conflicts} />
            </div>
          </div>
        )}

        {activeTab === 'schedule' && (
          <div className="space-y-6">
            <TrainScheduleTable trains={trains} onSelectTrain={(t) => setSelectedTrain(t)} />
          </div>
        )}

        {activeTab === 'recommendations' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
              <AiRecommendationPanel recommendations={recommendations} />
              <ConflictMonitor conflicts={conflicts} />
            </div>
            <OrToolsVisualizationPanel optimizationState={simState?.optimization_state} />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <AnalyticsView />
            {beforeAfter && <BeforeAfterComparison metrics={beforeAfter} />}
          </div>
        )}

        {activeTab === 'simulation' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
              <MlVisualizationPanel mlPrediction={simState?.ml_prediction} />
              <OrToolsVisualizationPanel optimizationState={simState?.optimization_state} />
            </div>
            <LiveSystemEventLog events={simState?.event_logs} />
            {beforeAfter && <BeforeAfterComparison metrics={beforeAfter} />}
          </div>
        )}
      </main>

      {/* Interactive Train Details Modal Drawer */}
      {selectedTrain && <TrainDetailModal train={selectedTrain} onClose={() => setSelectedTrain(null)} />}
    </div>
  );
}

export default App;
