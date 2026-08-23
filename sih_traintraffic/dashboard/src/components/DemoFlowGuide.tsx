import React from 'react';
import { ChevronRight, ChevronLeft, X, Play } from 'lucide-react';

interface DemoFlowGuideProps {
  currentStep: number;
  setCurrentStep: (step: number) => void;
  onClose: () => void;
  onSelectTab: (tab: string) => void;
  onRunOptimization: () => void;
}

export const DemoFlowGuide: React.FC<DemoFlowGuideProps> = ({
  currentStep,
  setCurrentStep,
  onClose,
  onSelectTab,
  onRunOptimization,
}) => {
  const steps = [
    {
      title: 'Step 1: Observe Current Railway State',
      tab: 'dashboard',
      actionText: 'View Replayed Telemetry',
      desc: 'Demonstrate active train positions replayed from RailRadar observation snapshots along the CSMT–Thane corridor.',
    },
    {
      title: 'Step 2: Show Train Delay & Risk Prediction',
      tab: 'schedule',
      actionText: 'Inspect Timetable',
      desc: 'Show scheduled vs expected ETAs, active train delays, and service priorities (Express, Local, Freight).',
    },
    {
      title: 'Step 3: Show Network Topology & Resources',
      tab: 'network',
      actionText: 'Inspect Network Map',
      desc: 'Show multi-track physical infrastructure graph (4-track CSMT-Sion, 6-track Kurla-Thane) with station nodes.',
    },
    {
      title: 'Step 4: Identify Predicted Conflict',
      tab: 'dashboard',
      actionText: 'Inspect Conflict Radar',
      desc: 'Highlight predicted headway and segment occupancy overlaps (e.g. T201 ↔ T305 at Dadar Block 4B).',
    },
    {
      title: 'Step 5: Show Random Forest Risk Signal',
      tab: 'schedule',
      actionText: 'Show ML Signals',
      desc: 'Explain how Random Forest Regressors & Classifiers predict delay escalation risks to weight solver priorities.',
    },
    {
      title: 'Step 6: Run Google OR-Tools CP-SAT',
      tab: 'simulation',
      actionText: 'Trigger Optimization',
      action: onRunOptimization,
      desc: 'Execute Google OR-Tools CP-SAT solver to compute a conflict-free dispatch schedule in real time.',
    },
    {
      title: 'Step 7: Show Recommended Dispatch & Allocation',
      tab: 'recommendations',
      actionText: 'View AI Recommendations',
      desc: 'Review CP-SAT recommendation cards detailing action types (PROCEED, HOLD, RESOURCE RE-ALLOCATION) and rationales.',
    },
    {
      title: 'Step 8: Show Modeled Headway Compliance',
      tab: 'network',
      actionText: 'Verify Safety Buffer',
      desc: 'Demonstrate that all train movements satisfy minimum 120s safety headway buffers between block occupancies.',
    },
    {
      title: 'Step 9: Compare Baseline vs Nexora',
      tab: 'dashboard',
      actionText: 'View Comparison',
      desc: 'Show side-by-side comparison between manual dispatch baseline and Google OR-Tools CP-SAT optimization.',
    },
    {
      title: 'Step 10: Show Delay/Hold/Conflict Improvements',
      tab: 'analytics',
      actionText: 'View Analytics',
      desc: 'Present the canonical 10-train benchmark showing 2.34% total delay reduction, 40.41% hold time saved, and 39.42% conflict reduction.',
    },
    {
      title: 'Step 11: Explain Prototype Assumptions',
      tab: 'dashboard',
      actionText: 'Review Assumptions',
      desc: 'Transparently walk through modeled logical resource assumptions, headway parameters, and offline telemetry replay scope.',
    },
    {
      title: 'Step 12: Show End-to-End System Architecture',
      tab: 'dashboard',
      actionText: 'Complete Walkthrough',
      desc: 'Summarize the complete pipeline: RailRadar Replay → Random Forest → Railway Graph → OR-Tools CP-SAT → Web Command Center.',
    },
  ];

  const activeStepObj = steps[currentStep] || steps[0];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      const nextIdx = currentStep + 1;
      setCurrentStep(nextIdx);
      onSelectTab(steps[nextIdx].tab);
      if (steps[nextIdx].action) {
        steps[nextIdx].action!();
      }
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      const prevIdx = currentStep - 1;
      setCurrentStep(prevIdx);
      onSelectTab(steps[prevIdx].tab);
    }
  };

  return (
    <div className="demo-guide-banner border-amber-500/40 bg-gradient-to-r from-slate-900 via-slate-900/95 to-amber-950/40 shadow-2xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40">
            <Play className="w-5 h-5 fill-current" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-extrabold text-amber-400 uppercase tracking-wider font-mono">
                SIH Judge Walkthrough Flow ({currentStep + 1} / {steps.length})
              </span>
              <span className="text-slate-500">•</span>
              <span className="text-xs font-bold text-slate-200">{activeStepObj.title}</span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5">{activeStepObj.desc}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <button
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed border border-slate-700"
              title="Previous Step"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span className="text-xs font-mono font-bold text-slate-300 px-2 py-1 bg-slate-950 rounded border border-slate-800">
              {currentStep + 1} of {steps.length}
            </span>

            <button
              onClick={handleNext}
              disabled={currentStep === steps.length - 1}
              className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1 shadow-lg transition"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-200" title="Exit Presentation Mode">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
