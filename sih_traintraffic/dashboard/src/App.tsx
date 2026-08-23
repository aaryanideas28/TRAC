import { useState, useEffect } from 'react';
import { apiService } from './services/apiService';
import type { StationNode, Train, AiRecommendation, ConflictItem, KpiMetrics, BeforeAfterMetrics } from './types/railway';
import { TopNav } from './components/TopNav';
import { KpiCards } from './components/KpiCards';
import { LiveRailwayNetwork } from './components/LiveRailwayNetwork';
import { BeforeAfterComparison } from './components/BeforeAfterComparison';
import { AiRecommendationPanel } from './components/AiRecommendationPanel';
import { ConflictMonitor } from './components/ConflictMonitor';
import { TrainScheduleTable } from './components/TrainScheduleTable';
import { AnalyticsView } from './components/AnalyticsView';
import { SimulationControl } from './components/SimulationControl';
import { TrainDetailModal } from './components/TrainDetailModal';
import { DemoFlowGuide } from './components/DemoFlowGuide';
import { DataProvenancePanel } from './components/DataProvenancePanel';
import { PrototypeAssumptionsPanel } from './components/PrototypeAssumptionsPanel';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [nodes, setNodes] = useState<StationNode[]>([]);
  const [trains, setTrains] = useState<Train[]>([]);
  const [recommendations, setRecommendations] = useState<AiRecommendation[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [metrics, setMetrics] = useState<KpiMetrics | null>(null);
  const [beforeAfter, setBeforeAfter] = useState<BeforeAfterMetrics | null>(null);

  const [selectedTrain, setSelectedTrain] = useState<Train | null>(null);
  const [systemStatus, setSystemStatus] = useState('ONLINE');
  const [lastUpdated, setLastUpdated] = useState('');

  // Demo walkthrough state
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoStep, setDemoStep] = useState(0);

  const updateClock = () => {
    const now = new Date();
    setLastUpdated(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  };

  const loadData = async () => {
    try {
      const net = await apiService.fetchNetwork();
      setNodes(net.nodes);

      const trs = await apiService.fetchTrains();
      setTrains(trs);

      const recs = await apiService.fetchRecommendations();
      setRecommendations(recs);

      const confs = await apiService.fetchConflicts();
      setConflicts(confs);

      const m = await apiService.fetchMetrics();
      setMetrics(m.kpis);
      setBeforeAfter(m.before_vs_after);

      setSystemStatus('ONLINE');
    } catch (e) {
      setSystemStatus('OFFLINE');
    }
    updateClock();
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 12000);
    return () => clearInterval(interval);
  }, []);

  const handleRunOptimization = async (config?: any) => {
    if (config) {
      await apiService.updateSimulation(config);
    }
    await apiService.runOptimization();
    await loadData();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* Top Header */}
      <TopNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        lastUpdated={lastUpdated}
        onRefresh={loadData}
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
            onRunOptimization={() => handleRunOptimization()}
          />
        </div>
      )}

      {/* Main Dashboard Layout Container */}
      <main className="w-full max-w-[1600px] mx-auto p-4 md:p-6 space-y-6">
        {/* Top Summary KPI Cards */}
        {metrics && <KpiCards metrics={metrics} />}

        {/* Dynamic Tab Views */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Live Interactive Railway Map */}
            <LiveRailwayNetwork
              nodes={nodes}
              trains={trains}
              onSelectTrain={(t) => setSelectedTrain(t)}
              selectedTrainId={selectedTrain?.id}
            />

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
            />
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
            <SimulationControl onRunOptimization={(cfg) => handleRunOptimization(cfg)} />
            {beforeAfter && <BeforeAfterComparison metrics={beforeAfter} />}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
              <AiRecommendationPanel recommendations={recommendations} />
              <ConflictMonitor conflicts={conflicts} />
            </div>
          </div>
        )}
      </main>

      {/* Interactive Train Details Modal Drawer */}
      {selectedTrain && <TrainDetailModal train={selectedTrain} onClose={() => setSelectedTrain(null)} />}
    </div>
  );
}

export default App;
