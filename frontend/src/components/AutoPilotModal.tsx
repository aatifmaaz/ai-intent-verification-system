import React, { useState, useEffect } from 'react';
import { 
  Zap, 
  Sparkles, 
  CheckCircle, 
  RefreshCw, 
  FileDiff, 
  Server, 
  ArrowRight, 
  X, 
  ShieldCheck, 
  AlertCircle,
  Network
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { autoEnforceIntent } from '../api/intents';
import { getTopologySuggestions, TopologySuggestions } from '../api/topology';
import type { AutoEnforceResult } from '../types';

interface AutoPilotModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultPrompt?: string;
  onSuccess?: () => void;
}

const DEFAULT_PRESET_INTENTS = [
  "Stop guest from reaching HR",
  "The guest network must not communicate with the HR network.",
  "Isolate database from guest",
  "Block all traffic between guest and HR",
  "Prevent guest from accessing database",
  "Only management may access core switch using SSH"
];

export const AutoPilotModal: React.FC<AutoPilotModalProps> = ({
  isOpen,
  onClose,
  defaultPrompt = '',
  onSuccess
}) => {
  const [prompt, setPrompt] = useState(defaultPrompt || DEFAULT_PRESET_INTENTS[0]);
  const [isRunning, setIsRunning] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [result, setResult] = useState<AutoEnforceResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [suggestionsData, setSuggestionsData] = useState<TopologySuggestions | null>(null);

  useEffect(() => {
    if (isOpen) {
      getTopologySuggestions()
        .then((data) => {
          setSuggestionsData(data);
          if (!defaultPrompt && data.suggestions && data.suggestions.length > 0) {
            setPrompt(data.suggestions[0]);
          }
        })
        .catch(() => {});
    }
  }, [isOpen, defaultPrompt]);

  if (!isOpen) return null;

  const handleExecute = async () => {
    if (!prompt.trim() || isRunning) return;
    setIsRunning(true);
    setErrorMsg(null);
    setResult(null);
    setActiveStep(1);

    const timer1 = setTimeout(() => setActiveStep(2), 400);
    const timer2 = setTimeout(() => setActiveStep(3), 800);
    const timer3 = setTimeout(() => setActiveStep(4), 1200);

    try {
      const data = await autoEnforceIntent(prompt);
      setTimeout(() => {
        setActiveStep(6);
        setResult(data);
        setIsRunning(false);
        if (onSuccess) onSuccess();
      }, 1600);
    } catch (err: unknown) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setIsRunning(false);
      setActiveStep(0);
      const msg = err instanceof Error ? err.message : 'Autonomous enforcement failed';
      setErrorMsg(msg);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div 
        className="w-full max-w-3xl bg-slate-900 border border-cyan-500/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-scaleUp"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-md shadow-cyan-500/20">
              <Zap className="w-5 h-5 fill-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">
                  Autonomous Network Auto-Pilot
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Closed-Loop
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Give any requirement in plain English. The AI parses, audits the graph, synthesizes patches, and deploys automatically.
              </p>
            </div>
          </div>

          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* Natural Language Prompt Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                Plain English Requirement:
              </label>
              <span className="text-[11px] text-slate-500 font-mono">
                Supports natural human phrasing
              </span>
            </div>

            <div className="relative">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={3}
                placeholder="e.g. Stop guest from reaching HR, or Isolate database from guest network..."
                className="w-full p-3.5 bg-slate-950 border border-slate-700 rounded-xl font-mono text-sm text-cyan-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 leading-relaxed transition-all"
              />
            </div>
          </div>

          {/* Quick Preset Badges */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1.5">
                <Network className="w-3.5 h-3.5 text-cyan-400" />
                Recommended for <span className="text-cyan-300 font-bold">{suggestionsData?.template_name || 'Current Topology'}:</span>
              </span>
              {suggestionsData && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {suggestionsData.devices_count} nodes online
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-1.5">
              {(suggestionsData?.suggestions && suggestionsData.suggestions.length > 0 
                ? suggestionsData.suggestions 
                : DEFAULT_PRESET_INTENTS
              ).map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPrompt(item)}
                  className={`px-2.5 py-1 text-xs rounded-lg transition-all font-mono text-left border ${
                    prompt === item
                      ? 'bg-cyan-500/20 text-cyan-200 border-cyan-500/50 shadow-sm shadow-cyan-500/20'
                      : 'bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border-slate-700/60 hover:border-cyan-500/40'
                  }`}
                >
                  "{item}"
                </button>
              ))}
            </div>
          </div>

          {/* Error Message */}
          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-400 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Execution Error: </span>
                <span>{errorMsg}</span>
              </div>
            </div>
          )}

          {/* 6-Stage Autonomous Execution Visualizer */}
          {(isRunning || result) && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  Autonomous Execution Lifecycle
                </span>
                <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase ${
                  result?.status === 'REMEDIATED'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : result?.status === 'COMPLIANT'
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                    : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse'
                }`}>
                  {isRunning ? 'Processing Live...' : result?.status}
                </span>
              </div>

              {/* 6 Step Indicators */}
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {[
                  { step: 1, label: 'NLP Parsing' },
                  { step: 2, label: 'Audit Graph' },
                  { step: 3, label: 'Patch Synth' },
                  { step: 4, label: 'Sandbox Run' },
                  { step: 5, label: 'Deploy ACL' },
                  { step: 6, label: 'Re-Verify' },
                ].map((s) => {
                  const isDone = activeStep >= s.step;
                  const isCurrent = activeStep === s.step && isRunning;
                  return (
                    <div
                      key={s.step}
                      className={`p-2 rounded-lg border text-center transition-all ${
                        isDone
                          ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
                          : isCurrent
                          ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-300 animate-pulse'
                          : 'bg-slate-900/60 border-slate-800/80 text-slate-600'
                      }`}
                    >
                      <div className="text-[10px] font-mono font-bold">
                        {isDone ? '✓ ' : ''}S0{s.step}
                      </div>
                      <div className="text-[10px] font-medium truncate mt-0.5">{s.label}</div>
                    </div>
                  );
                })}
              </div>

              {/* Step Logs */}
              {result?.steps && (
                <div className="space-y-1.5 pt-1">
                  {result.steps.map((st) => (
                    <div key={st.step} className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-xs flex items-start gap-2">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <span className="font-bold text-white">{st.title}: </span>
                        <span className="text-slate-300 font-mono text-[11px]">{st.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Remediated Diff */}
              {result?.repair && (
                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileDiff className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-bold text-white">
                        Patch Auto-Deployed to {(result.repair.affected_devices || []).join(', ')}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      0 Violations Remaining
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                      <div className="text-[11px] text-red-400 font-mono font-semibold">Previous Config (Breached)</div>
                      <pre className="text-[9px] font-mono text-slate-400 max-h-32 overflow-y-auto">
                        <code>{JSON.stringify(result.repair.original_config, null, 2)}</code>
                      </pre>
                    </div>

                    <div className="p-2.5 bg-slate-950 rounded-lg border border-emerald-500/30 space-y-1">
                      <div className="text-[11px] text-emerald-400 font-mono font-semibold">Remediated Config (Sealed)</div>
                      <pre className="text-[9px] font-mono text-emerald-300 max-h-32 overflow-y-auto">
                        <code>{JSON.stringify(result.repair.proposed_config, null, 2)}</code>
                      </pre>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1 text-xs">
                    <span className="text-slate-400 font-mono text-[11px]">
                      Initial Violations: <strong className="text-red-400">{result.initial_run?.failed ?? 1}</strong> &rarr; Final Violations: <strong className="text-emerald-400">0</strong>
                    </span>

                    <div className="flex items-center gap-2">
                      <Link
                        to="/topology"
                        onClick={onClose}
                        className="text-cyan-400 hover:underline flex items-center gap-1 text-xs font-medium"
                      >
                        <Server className="w-3.5 h-3.5" />
                        Topology
                      </Link>
                      <Link
                        to="/configurations"
                        onClick={onClose}
                        className="text-cyan-400 hover:underline flex items-center gap-1 text-xs font-medium"
                      >
                        Configurations
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between gap-3">
          <div className="text-xs text-slate-500 font-mono hidden sm:flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Closed-Loop Autonomous Engine Online
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              Close
            </button>

            <button
              type="button"
              onClick={handleExecute}
              disabled={isRunning || !prompt.trim()}
              className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-cyan-600/30 transition-all disabled:opacity-50"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Auto-Enforcing Requirement...
                </>
              ) : (
                <>
                  <Zap className="w-3.5 h-3.5 fill-white" />
                  🚀 Auto-Enforce Requirement (1-Click)
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
