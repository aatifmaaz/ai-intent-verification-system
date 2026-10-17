import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getSystemStatus, resetSystemTopology } from '../api/system';
import { runVerification } from '../api/verification';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { 
  Settings as SettingsIcon, 
  Activity, 
  RotateCcw, 
  Download, 
  CheckCircle, 
  Cpu, 
  Sliders, 
  AlertTriangle,
  Play
} from 'lucide-react';


export const Settings: React.FC = () => {
  const { data: status, loading, error, refetch } = useApi(getSystemStatus);

  // Settings State (local simulated preferences)
  const [verificationMode, setVerificationMode] = useState<'strict' | 'permissive'>('strict');
  const [nlpParserMode, setNlpParserMode] = useState<'deterministic' | 'hybrid'>('deterministic');
  const [maxHops, setMaxHops] = useState<number>(10);
  const [autoValidate, setAutoValidate] = useState<boolean>(true);

  // Action status
  const [resetting, setResetting] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleReset = async () => {
    if (!window.confirm('Reset network database, topology, and policies to baseline 15-device state?')) return;
    setResetting(true);
    setNotice(null);
    try {
      const res = await resetSystemTopology();
      setNotice({ type: 'success', text: res.message });
      refetch();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Reset failed';
      setNotice({ type: 'error', text: `Failed to reset: ${msg}` });
    } finally {
      setResetting(false);
    }
  };

  const handleRunFullVerification = async () => {
    setVerifying(true);
    setNotice(null);
    try {
      const run = await runVerification();
      setNotice({ 
        type: 'success', 
        text: `Full verification completed: ${run.passed} passed, ${run.failed} failed, ${run.unknown} unknown.` 
      });
      refetch();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Verification failed';
      setNotice({ type: 'error', text: `Verification run failed: ${msg}` });
    } finally {
      setVerifying(false);
    }
  };

  const handleExportSnapshot = () => {
    if (!status) return;
    const snapshot = {
      timestamp: new Date().toISOString(),
      system_status: status,
      settings: {
        verificationMode,
        nlpParserMode,
        maxHops,
        autoValidate
      }
    };
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `niv_platform_snapshot_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !status) return <LoadingSpinner message="Checking platform health and status..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <SettingsIcon className="w-7 h-7 text-cyan-400" />
          System Settings & Platform Health
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure deterministic verification algorithms, tune NLP parsing strictness, and monitor simulation health
        </p>
      </div>

      {notice && (
        <div className={`p-4 rounded-xl border flex items-center justify-between text-sm ${
          notice.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
            : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          <div className="flex items-center gap-3">
            {notice.type === 'success' ? (
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            )}
            <span>{notice.text}</span>
          </div>
          <button onClick={() => setNotice(null)} className="text-xs hover:underline">Dismiss</button>
        </div>
      )}

      {/* Platform Health Status Cards */}
      <div className="card p-6 space-y-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          Live Platform Diagnostics
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-xs text-slate-500 font-mono">Backend API</span>
            <div className="text-base font-bold text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Operational
            </div>
            <span className="text-[11px] text-slate-400 font-mono">FastAPI / SQLite</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-xs text-slate-500 font-mono">Engine Version</span>
            <div className="text-base font-bold text-white font-mono">{status?.engine_version || '2.4.0'}</div>
            <span className="text-[11px] text-cyan-400 font-mono">{status?.mode || 'Graph + NLP'}</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-xs text-slate-500 font-mono">Monitored Devices</span>
            <div className="text-base font-bold text-white font-mono">{status?.devices_count || 0} Nodes</div>
            <span className="text-[11px] text-slate-400 font-mono">{status?.links_count || 0} Mesh Links</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-xs text-slate-500 font-mono">Active Intents</span>
            <div className="text-base font-bold text-white font-mono">{status?.intents_count || 0} Policies</div>
            <span className="text-[11px] text-amber-400 font-mono">{status?.pending_repairs || 0} Pending Repairs</span>
          </div>
        </div>
      </div>

      {/* Engine Tuning Parameters */}
      <div className="card p-6 space-y-5">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Sliders className="w-4 h-4 text-cyan-400" />
          Verification & Parsing Parameters
        </h2>

        <div className="space-y-4">
          {/* Verification Mode */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
            <div>
              <div className="text-sm font-semibold text-white">Verification Engine Strictness</div>
              <div className="text-xs text-slate-400">Zero-Trust assumes implicit deny unless an explicit allow path exists</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setVerificationMode('strict')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  verificationMode === 'strict'
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30'
                    : 'bg-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                Strict (Zero-Trust)
              </button>
              <button
                onClick={() => setVerificationMode('permissive')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  verificationMode === 'permissive'
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30'
                    : 'bg-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                Permissive
              </button>
            </div>
          </div>

          {/* NLP Parsing Engine */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
            <div>
              <div className="text-sm font-semibold text-white">Natural Language Intent Parser Mode</div>
              <div className="text-xs text-slate-400">Deterministic grammar guarantees reproducible, auditable policy generation</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setNlpParserMode('deterministic')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  nlpParserMode === 'deterministic'
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30'
                    : 'bg-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                Deterministic Rules
              </button>
              <button
                onClick={() => setNlpParserMode('hybrid')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  nlpParserMode === 'hybrid'
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30'
                    : 'bg-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                Hybrid (Regex + LLM)
              </button>
            </div>
          </div>

          {/* Max Graph Search Depth */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
            <div>
              <div className="text-sm font-semibold text-white">Max Graph Traversal Depth</div>
              <div className="text-xs text-slate-400">Limits search hop radius during reachability path BFS/DFS analysis</div>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="3"
                max="25"
                value={maxHops}
                onChange={(e) => setMaxHops(Number(e.target.value))}
                className="w-32 accent-cyan-500"
              />
              <span className="font-mono text-xs font-bold text-cyan-400 w-12 text-right">
                {maxHops} hops
              </span>
            </div>
          </div>

          {/* Auto Validate Toggle */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
            <div>
              <div className="text-sm font-semibold text-white">Pre-Validate Automated Repairs</div>
              <div className="text-xs text-slate-400">Automatically run isolated sandbox regression checks before showing proposal</div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoValidate}
                onChange={(e) => setAutoValidate(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-600"></div>
            </label>
          </div>
        </div>
      </div>

      {/* Administrative Actions */}
      <div className="card p-6 space-y-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          Maintenance & Operations
        </h2>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleRunFullVerification}
            disabled={verifying}
            className="flex items-center gap-2 px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow-md shadow-cyan-600/20 disabled:opacity-50 transition-all"
          >
            <Play className="w-4 h-4" />
            {verifying ? 'Executing...' : 'Run Full Network Verification'}
          </button>

          <button
            onClick={handleReset}
            disabled={resetting}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-amber-400 hover:text-amber-300 text-xs font-semibold rounded-lg border border-amber-500/30 disabled:opacity-50 transition-all"
          >
            <RotateCcw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} />
            {resetting ? 'Resetting...' : 'Reset Database to 15-Device Baseline'}
          </button>

          <button
            onClick={handleExportSnapshot}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition-all"
          >
            <Download className="w-4 h-4" />
            Export System Snapshot (JSON)
          </button>
        </div>
      </div>

      {/* About Box */}
      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-500 space-y-1 font-mono">
        <div>AI-Driven Network Intent Verification &amp; Automated Configuration Repair</div>
        <div>FastAPI &middot; React 18 &middot; TypeScript &middot; NetworkX Graph Algorithms &middot; MIT License</div>
      </div>
    </div>
  );
};
