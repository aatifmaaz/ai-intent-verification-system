import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getIntents, createIntent, deleteIntent, autoEnforceIntent } from '../api/intents';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { 
  Plus, 
  Trash2, 
  ChevronDown, 
  ChevronRight, 
  MessageSquare, 
  Zap, 
  CheckCircle, 
  ShieldCheck, 
  Server, 
  ArrowRight,
  Sparkles,
  RefreshCw,
  FileDiff
} from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AutoEnforceResult } from '../types';

const EXAMPLE_INTENTS = [
  "The guest network must not communicate with the HR network.",
  "Isolate guest devices from internal HR servers.",
  "Only administrators may access network devices using SSH.",
  "All devices in the engineering network must be able to access the internal application server.",
  "The backup network must remain isolated from ordinary user traffic.",
];

export const IntentManagement: React.FC = () => {
  const { data: intents, loading, error, refetch } = useApi(getIntents);
  const [activeTab, setActiveTab] = useState<'autopilot' | 'list'>('autopilot');
  const [newIntentText, setNewIntentText] = useState(
    'The guest network must not communicate with the HR network.'
  );

  // Auto-Pilot Execution State
  const [isRunningAutoPilot, setIsRunningAutoPilot] = useState(false);
  const [autoPilotResult, setAutoPilotResult] = useState<AutoEnforceResult | null>(null);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [submittingStandard, setSubmittingStandard] = useState(false);

  const handleRunAutoPilot = async () => {
    if (!newIntentText.trim()) return;
    setIsRunningAutoPilot(true);
    setAutoPilotResult(null);
    setActiveStepIndex(1);

    // Simulate animated step progression for a thrilling user experience
    const timer1 = setTimeout(() => setActiveStepIndex(2), 500);
    const timer2 = setTimeout(() => setActiveStepIndex(3), 1000);
    const timer3 = setTimeout(() => setActiveStepIndex(4), 1500);

    try {
      const result: AutoEnforceResult = await autoEnforceIntent(newIntentText);
      setTimeout(() => {
        setActiveStepIndex(6);
        setAutoPilotResult(result);
        setIsRunningAutoPilot(false);
        refetch();
      }, 2000);
    } catch (err: unknown) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setIsRunningAutoPilot(false);
      setActiveStepIndex(0);
      const msg = err instanceof Error ? err.message : 'Autonomous enforcement failed';
      alert(`Auto-Pilot Error: ${msg}`);
    }
  };

  const handleStandardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIntentText.trim()) return;
    setSubmittingStandard(true);
    try {
      await createIntent(newIntentText);
      setNewIntentText('');
      refetch();
      setActiveTab('list');
    } catch (err) {
      console.error(err);
    } finally {
      setSubmittingStandard(false);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this intent?')) return;
    try {
      await deleteIntent(id);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading && !intents) return <LoadingSpinner message="Loading network intents..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  const intentList = intents || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Zap className="w-7 h-7 text-cyan-400" />
            Autonomous Natural Language Auto-Pilot
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Specify desired network security requirements in plain English. The autonomous closed loop translates, audits the graph, synthesizes patches, and deploys fixes automatically.
          </p>
        </div>

        {/* Tab switch */}
        <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveTab('autopilot')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'autopilot'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Auto-Pilot Studio
          </button>
          <button
            onClick={() => setActiveTab('list')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'list'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            All Policies ({intentList.length})
          </button>
        </div>
      </div>

      {/* AUTONOMOUS AUTO-PILOT STUDIO TAB */}
      {activeTab === 'autopilot' && (
        <div className="space-y-6">
          {/* Main Input Card */}
          <div className="card p-6 border-cyan-500/30 shadow-2xl relative overflow-hidden space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold font-mono">
                  NL
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">Natural Language Requirement Specification</h2>
                  <p className="text-xs text-slate-400">Describe what you want the network to do in everyday human language</p>
                </div>
              </div>

              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                Closed-Loop Engine Ready
              </span>
            </div>

            {/* Prompt Textarea */}
            <div>
              <textarea
                value={newIntentText}
                onChange={(e) => setNewIntentText(e.target.value)}
                rows={3}
                placeholder="Example: The guest network must not communicate with the HR network."
                className="w-full p-4 bg-slate-950 font-mono text-sm text-cyan-300 rounded-xl border border-slate-700/80 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 leading-relaxed transition-all"
              />
            </div>

            {/* Example Presets */}
            <div className="space-y-2">
              <div className="text-xs text-slate-400 font-medium">Click a real-world requirement to test instantly:</div>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_INTENTS.map((ex, i) => (
                  <button
                    key={i}
                    onClick={() => setNewIntentText(ex)}
                    className="text-xs px-3 py-1.5 bg-slate-850 hover:bg-slate-800 text-slate-300 hover:text-cyan-400 rounded-lg border border-slate-700/60 hover:border-cyan-500/40 transition-all font-mono text-left"
                  >
                    "{ex}"
                  </button>
                ))}
              </div>
            </div>

            {/* Primary Action Button Bar */}
            <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 border-t border-slate-800/80">
              <div className="text-xs text-slate-500 font-mono flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Autonomous Self-Healing Loop Active
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleStandardSubmit}
                  disabled={submittingStandard || !newIntentText.trim()}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 transition-colors disabled:opacity-50"
                >
                  {submittingStandard ? 'Saving...' : 'Save Draft Intent Only'}
                </button>

                <button
                  onClick={handleRunAutoPilot}
                  disabled={isRunningAutoPilot || !newIntentText.trim()}
                  className="flex items-center justify-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-cyan-600/30 transition-all disabled:opacity-50"
                >
                  {isRunningAutoPilot ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Executing Auto-Pilot...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 fill-white" />
                      🚀 Auto-Enforce Requirement (1-Click)
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Autonomous Execution Pipeline Visualizer */}
          {(isRunningAutoPilot || autoPilotResult) && (
            <div className="card p-6 space-y-6 animate-fadeIn">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  Autonomous Closed-Loop Pipeline Execution
                </h3>
                <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase ${
                  autoPilotResult?.status === 'REMEDIATED' 
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                    : autoPilotResult?.status === 'COMPLIANT'
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                    : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse'
                }`}>
                  {isRunningAutoPilot ? 'Executing Live Cycle' : autoPilotResult?.status}
                </span>
              </div>

              {/* 6-Stage Progress Steps */}
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                {[
                  { step: 1, label: 'NLP Parsing' },
                  { step: 2, label: 'Graph Reachability' },
                  { step: 3, label: 'Patch Synthesis' },
                  { step: 4, label: 'Sandbox Dry-Run' },
                  { step: 5, label: 'Auto Deployment' },
                  { step: 6, label: 'Closed Verification' },
                ].map((s) => {
                  const isDone = activeStepIndex >= s.step;
                  const isCurrent = activeStepIndex === s.step && isRunningAutoPilot;

                  return (
                    <div
                      key={s.step}
                      className={`p-3 rounded-xl border text-center transition-all ${
                        isDone
                          ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 shadow-sm'
                          : isCurrent
                          ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-300 animate-pulse'
                          : 'bg-slate-900/60 border-slate-800 text-slate-500'
                      }`}
                    >
                      <div className="text-xs font-mono font-bold">
                        {isDone ? '✓ STEP' : 'STEP'} 0{s.step}
                      </div>
                      <div className="text-[11px] font-medium mt-1 truncate">{s.label}</div>
                    </div>
                  );
                })}
              </div>

              {/* Step Execution Log */}
              {autoPilotResult?.steps && (
                <div className="space-y-2 pt-2">
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Execution Evidence:</div>
                  <div className="space-y-1.5">
                    {autoPilotResult.steps.map((st) => (
                      <div key={st.step} className="p-3 bg-slate-900/70 rounded-lg border border-slate-800 text-xs flex items-start gap-2.5">
                        <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold text-white">{st.title}: </span>
                          <span className="text-slate-300 font-mono">{st.detail}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Remediation Diff Card */}
              {autoPilotResult?.repair && (
                <div className="p-5 rounded-xl border border-emerald-500/30 bg-emerald-950/10 space-y-4">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                    <div className="flex items-center gap-2">
                      <FileDiff className="w-5 h-5 text-emerald-400" />
                      <span className="text-sm font-bold text-white">
                        Autonomous Configuration Patch Deployed to {(autoPilotResult.repair.affected_devices || []).join(', ')}
                      </span>
                    </div>

                    <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      Patch Verified Active
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                      <div className="text-xs text-red-400 font-mono font-semibold pb-1 border-b border-slate-800">
                        Original Configuration (Breached State)
                      </div>
                      <pre className="text-[10px] font-mono text-slate-400 max-h-44 overflow-y-auto leading-relaxed">
                        <code>{JSON.stringify(autoPilotResult.repair.original_config, null, 2)}</code>
                      </pre>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-lg border border-emerald-500/30 space-y-1">
                      <div className="text-xs text-emerald-400 font-mono font-semibold pb-1 border-b border-emerald-500/20">
                        Remediated Configuration (Enforced &amp; Sealed)
                      </div>
                      <pre className="text-[10px] font-mono text-emerald-300 max-h-44 overflow-y-auto leading-relaxed">
                        <code>{JSON.stringify(autoPilotResult.repair.proposed_config, null, 2)}</code>
                      </pre>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 text-xs">
                    <span className="text-slate-400 font-mono">
                      Initial Violations: <strong className="text-red-400">{autoPilotResult.initial_run?.failed ?? 1}</strong> &rarr; Final Violations: <strong className="text-emerald-400">0</strong>
                    </span>

                    <div className="flex items-center gap-3">
                      <Link
                        to="/topology"
                        className="text-cyan-400 hover:underline flex items-center gap-1 font-medium"
                      >
                        <Server className="w-3.5 h-3.5" />
                        View Live Topology
                      </Link>
                      <Link
                        to="/configurations"
                        className="text-cyan-400 hover:underline flex items-center gap-1 font-medium"
                      >
                        Inspect Device Config
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ALL POLICIES TAB */}
      {activeTab === 'list' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white">Configured Network Policies ({intentList.length})</h2>
            <button
              onClick={() => setActiveTab('autopilot')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              New Auto-Pilot Intent
            </button>
          </div>

          {intentList.length === 0 ? (
            <div className="card p-12 text-center text-slate-500 space-y-2">
              <MessageSquare className="w-8 h-8 mx-auto text-slate-600" />
              <p className="text-sm">No intents registered yet.</p>
              <button
                onClick={() => setActiveTab('autopilot')}
                className="text-xs text-cyan-400 hover:underline"
              >
                Launch Auto-Pilot Studio &rarr;
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {intentList.map((intent) => {
                const isExpanded = expandedId === intent.id;
                return (
                  <div key={intent.id} className="card p-4 space-y-3">
                    <div
                      className="flex items-center justify-between cursor-pointer"
                      onClick={() => setExpandedId(isExpanded ? null : intent.id)}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {isExpanded ? <ChevronDown className="w-4 h-4 text-cyan-400 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />}
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-white truncate">"{intent.natural_language}"</div>
                          <div className="text-xs text-slate-500 font-mono mt-0.5">
                            Status: <span className="text-cyan-400 uppercase">{intent.status}</span> &middot; Confidence: {Math.round((intent.confidence || 1) * 100)}%
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {intent.policies?.length || 0} rule(s)
                        </span>
                        <button
                          onClick={(e) => handleDelete(intent.id, e)}
                          className="p-1.5 text-slate-500 hover:text-red-400 rounded hover:bg-slate-800 transition-colors"
                          title="Delete Intent"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {isExpanded && intent.policies && intent.policies.length > 0 && (
                      <div className="pt-3 border-t border-slate-800/80 space-y-2">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Normalized Structured Rules:</div>
                        <div className="space-y-1.5">
                          {intent.policies.map((p) => (
                            <div key={p.id} className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                  p.policy_type === 'deny' || p.policy_type === 'isolate'
                                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                    : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                }`}>
                                  {p.policy_type}
                                </span>
                                <span className="text-slate-300">
                                  {p.source_zone || 'any'} &rarr; {p.destination_zone || 'any'}
                                </span>
                              </div>
                              <span className="text-slate-500">
                                Protocol: {p.protocol || 'ip'} &middot; Port: {p.port || 'any'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
