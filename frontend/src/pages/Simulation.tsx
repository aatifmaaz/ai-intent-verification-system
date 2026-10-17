import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getScenarios, runScenario, resetBaselineTopology } from '../api/scenarios';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import type { ScenarioResult } from '../types';
import { 
  FlaskConical, 
  Play, 
  RotateCcw, 
  CheckCircle, 
  ShieldAlert, 
  ArrowRight, 
  Zap, 
  Server, 
  Activity
} from 'lucide-react';
import { Link } from 'react-router-dom';


export const Simulation: React.FC = () => {
  const { data: scenarios, loading, error, refetch } = useApi(getScenarios);
  const [activeScenarioId, setActiveScenarioId] = useState<string>('A');
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResult | null>(null);
  const [executionStep, setExecutionStep] = useState<number>(0);
  const [resettingBaseline, setResettingBaseline] = useState(false);
  const [resetNotice, setResetNotice] = useState<string | null>(null);

  const handleRunScenario = async (id: string) => {
    setRunningScenario(id);
    setScenarioResult(null);
    setResetNotice(null);
    setExecutionStep(1); // Stage 1: Injecting fault

    setTimeout(() => setExecutionStep(2), 600); // Stage 2: Graph verification
    setTimeout(() => setExecutionStep(3), 1200); // Stage 3: Identifying violation

    try {
      const result = await runScenario(id);
      setTimeout(() => {
        setExecutionStep(4); // Stage 4: Completed
        setScenarioResult(result);
        setRunningScenario(null);
      }, 1800);
    } catch (err: unknown) {
      console.error(err);
      setRunningScenario(null);
      setExecutionStep(0);
      alert('Failed to execute scenario simulation.');
    }
  };

  const handleResetBaseline = async () => {
    if (!window.confirm('Reset network topology and policies back to default 15-device baseline?')) return;
    setResettingBaseline(true);
    setResetNotice(null);
    try {
      const res = await resetBaselineTopology();
      setResetNotice(res.message);
      setScenarioResult(null);
      setExecutionStep(0);
    } catch (err: unknown) {
      console.error(err);
      alert('Failed to reset topology baseline.');
    } finally {
      setResettingBaseline(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading scenario simulation catalog..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  const scenarioList = scenarios || [];
  const selectedScenario = scenarioList.find(s => s.id === activeScenarioId) || scenarioList[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FlaskConical className="w-7 h-7 text-cyan-400" />
            Network Simulation & Fault Injection Lab
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Simulate real-world enterprise fault scenarios, verify deterministic graph reachability, and observe automated policy remediation
          </p>
        </div>

        <button
          onClick={handleResetBaseline}
          disabled={resettingBaseline}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 hover:text-cyan-300 text-sm font-semibold rounded-lg border border-cyan-500/30 transition-all shadow-sm"
        >
          <RotateCcw className={`w-4 h-4 ${resettingBaseline ? 'animate-spin' : ''}`} />
          {resettingBaseline ? 'Resetting...' : 'Reset 15-Device Baseline'}
        </button>
      </div>

      {resetNotice && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
            <span>{resetNotice}</span>
          </div>
          <button onClick={() => setResetNotice(null)} className="text-emerald-400 hover:underline text-xs">Dismiss</button>
        </div>
      )}

      {/* Main Grid: Scenario Selector on Left, Interactive Simulation Studio on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Scenario Catalog */}
        <div className="lg:col-span-1 space-y-3">
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Demo Scenarios (A - E)</h2>
              <span className="text-xs bg-slate-800 text-cyan-400 px-2 py-0.5 rounded-full font-mono">{scenarioList.length}</span>
            </div>

            <div className="space-y-2">
              {scenarioList.map((scenario) => {
                const isSelected = scenario.id === activeScenarioId;
                return (
                  <button
                    key={scenario.id}
                    onClick={() => {
                      setActiveScenarioId(scenario.id);
                      setScenarioResult(null);
                      setExecutionStep(0);
                    }}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                      isSelected
                        ? 'bg-cyan-500/10 border-cyan-500/50 shadow-md shadow-cyan-500/10'
                        : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="px-2 py-0.5 rounded font-mono font-bold text-xs bg-slate-800 text-cyan-400 border border-slate-700">
                        SCENARIO {scenario.id}
                      </span>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                        scenario.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                        scenario.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      }`}>
                        {scenario.severity}
                      </span>
                    </div>

                    <div className="text-sm font-semibold text-white truncate">{scenario.name}</div>
                    <div className="text-xs text-slate-400 mt-1 line-clamp-2">{scenario.category}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Simulation Stage */}
        <div className="lg:col-span-2 space-y-6">
          {selectedScenario && (
            <div className="card p-6 space-y-6">
              {/* Scenario Overview */}
              <div className="space-y-3 pb-6 border-b border-slate-800">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <span className="text-xs font-mono uppercase text-cyan-400 tracking-wider">
                      {selectedScenario.category}
                    </span>
                    <h2 className="text-xl font-bold text-white mt-1">
                      Scenario {selectedScenario.id}: {selectedScenario.name}
                    </h2>
                  </div>

                  <button
                    onClick={() => handleRunScenario(selectedScenario.id)}
                    disabled={runningScenario !== null}
                    className="flex items-center gap-2 px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-cyan-600/30 transition-all disabled:opacity-50"
                  >
                    {runningScenario ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Simulating Flow...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-white" />
                        Execute Simulation
                      </>
                    )}
                  </button>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed">
                  {selectedScenario.description}
                </p>

                {selectedScenario.attack_vector && (
                  <div className="p-3 rounded-lg bg-red-950/20 border border-red-500/30 text-xs text-red-300 flex items-start gap-2.5">
                    <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-red-400">Risk Vector: </strong>
                      {selectedScenario.attack_vector}
                    </div>
                  </div>
                )}
              </div>

              {/* Execution Pipeline Steps */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Deterministic Execution Pipeline
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  {[
                    { step: 1, label: 'Inject Topology & Rules' },
                    { step: 2, label: 'Graph Reachability' },
                    { step: 3, label: 'Policy Verification' },
                    { step: 4, label: 'Root Cause & Patch' },
                  ].map((s) => {
                    const isDone = executionStep > s.step || (executionStep === 4 && s.step === 4);
                    const isCurrent = executionStep === s.step && runningScenario !== null;

                    return (
                      <div
                        key={s.step}
                        className={`p-3 rounded-xl border text-center transition-all ${
                          isDone
                            ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
                            : isCurrent
                            ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-300 animate-pulse'
                            : 'bg-slate-900/60 border-slate-800 text-slate-500'
                        }`}
                      >
                        <div className="text-xs font-mono font-bold">
                          {isDone ? '✓ STEP' : 'STEP'} 0{s.step}
                        </div>
                        <div className="text-xs font-medium mt-1 truncate">{s.label}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Visual Packet Path Tracer Diagram */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <Zap className="w-4 h-4 text-cyan-400" />
                    Simulated Packet Flow Path
                  </h3>
                  <span className="text-xs font-mono text-slate-500">
                    Source: {selectedScenario.affected_zones?.[0] || 'Client'} → Dest: {selectedScenario.affected_zones?.[selectedScenario.affected_zones.length - 1] || 'Target'}
                  </span>
                </div>

                <div className="p-6 bg-slate-950/80 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
                  {/* Source Node */}
                  <div className="flex flex-col items-center gap-2 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 shadow-lg shadow-blue-500/10">
                      <Server className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">{selectedScenario.target_devices?.[0] || 'source-node'}</div>
                      <span className="text-[10px] text-blue-400 uppercase font-mono">{selectedScenario.affected_zones?.[0] || 'Zone A'}</span>
                    </div>
                  </div>

                  {/* Flow Arrow with Packet Animation */}
                  <div className="flex-1 flex flex-col items-center px-4 w-full sm:w-auto">
                    <div className="w-full flex items-center justify-center gap-1 relative">
                      <div className={`h-1 flex-1 rounded ${
                        executionStep >= 3 ? 'bg-red-500/60' : 'bg-slate-700'
                      }`} />
                      <div className={`w-3 h-3 rounded-full ${
                        executionStep >= 3 ? 'bg-red-400 animate-ping' : 'bg-slate-500'
                      }`} />
                      <div className={`h-1 flex-1 rounded ${
                        executionStep >= 3 ? 'bg-red-500/60' : 'bg-slate-700'
                      }`} />
                    </div>
                    <span className={`text-[10px] font-mono mt-2 font-bold ${
                      executionStep >= 3 ? 'text-red-400' : 'text-slate-500'
                    }`}>
                      {executionStep >= 3 ? '⚡ VIOLATING TRAFFIC FLOW DETECTED' : 'Idle Simulation Path'}
                    </span>
                  </div>

                  {/* Intermediary Enforcer */}
                  <div className="flex flex-col items-center gap-2 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
                      <ShieldAlert className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">{selectedScenario.target_devices?.[1] || 'core-gateway'}</div>
                      <span className="text-[10px] text-amber-400 uppercase font-mono">Enforcer Node</span>
                    </div>
                  </div>

                  {/* Flow Arrow 2 */}
                  <div className="flex-1 flex flex-col items-center px-4 w-full sm:w-auto">
                    <div className="w-full flex items-center justify-center gap-1 relative">
                      <div className={`h-1 flex-1 rounded ${
                        executionStep >= 3 ? 'bg-red-500/60' : 'bg-slate-700'
                      }`} />
                      <div className={`w-3 h-3 rounded-full ${
                        executionStep >= 3 ? 'bg-red-400 animate-ping' : 'bg-slate-500'
                      }`} />
                      <div className={`h-1 flex-1 rounded ${
                        executionStep >= 3 ? 'bg-red-500/60' : 'bg-slate-700'
                      }`} />
                    </div>
                    <span className={`text-[10px] font-mono mt-2 font-bold ${
                      executionStep >= 3 ? 'text-red-400' : 'text-slate-500'
                    }`}>
                      {executionStep >= 3 ? 'Breached Boundary' : 'Forwarding Stage'}
                    </span>
                  </div>

                  {/* Destination Node */}
                  <div className="flex flex-col items-center gap-2 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-500/10">
                      <Server className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">{selectedScenario.target_devices?.[2] || 'target-server'}</div>
                      <span className="text-[10px] text-emerald-400 uppercase font-mono">{selectedScenario.affected_zones?.[selectedScenario.affected_zones.length - 1] || 'Target Zone'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Simulation Result Box */}
              {scenarioResult && (
                <div className="p-5 rounded-xl border border-red-500/30 bg-red-950/20 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-red-400 font-bold text-sm">
                      <ShieldAlert className="w-5 h-5 flex-shrink-0" />
                      <span>Policy Breach Verified: {scenarioResult.findings.length} Violation Finding(s) Identified</span>
                    </div>

                    <span className="px-2.5 py-0.5 rounded font-mono text-xs font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                      STATUS: FAIL
                    </span>
                  </div>

                  {scenarioResult.findings.map((f, idx) => (
                    <div key={idx} className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 text-xs space-y-2">
                      <div className="text-slate-200 font-mono leading-relaxed">{f.details}</div>
                      {f.remediation && (
                        <div className="text-emerald-400 font-medium flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 flex-shrink-0" />
                          <span>Remediation Advice: {f.remediation}</span>
                        </div>
                      )}
                    </div>
                  ))}

                  <div className="flex items-center justify-end pt-2">
                    <Link
                      to="/repairs"
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-md shadow-emerald-600/20 transition-all"
                    >
                      Review & Apply Automated Patch in Repair Center
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
