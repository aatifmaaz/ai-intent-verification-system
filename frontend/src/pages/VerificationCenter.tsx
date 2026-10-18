import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getVerificationResults, runVerification, proposeRepair } from '../api/verification';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Play, ShieldCheck, ShieldAlert, CheckCircle, HelpCircle, ChevronDown, ChevronRight, Wrench, Filter, ArrowRight, Zap, Sparkles } from 'lucide-react';
import { VerificationRun, VerificationFinding } from '../types';
import { AutoPilotModal } from '../components/AutoPilotModal';

export const VerificationCenter = () => {
  const { data: runs, loading, error, refetch } = useApi(getVerificationResults);
  const [isRunning, setIsRunning] = useState(false);
  const [latestRun, setLatestRun] = useState<VerificationRun | null>(null);
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [proposingRepair, setProposingRepair] = useState<number | null>(null);
  const [repairSuccessNotice, setRepairSuccessNotice] = useState<{ id: number; message: string } | null>(null);
  const [isAutoPilotOpen, setIsAutoPilotOpen] = useState(false);
  const [autoPilotPrompt, setAutoPilotPrompt] = useState('Stop guest from reaching HR');


  const handleRunVerification = async () => {
    setIsRunning(true);
    setRepairSuccessNotice(null);
    try {
      const result = await runVerification();
      setLatestRun(result);
      refetch();
    } catch (err) {
      console.error(err);
    } finally {
      setIsRunning(false);
    }
  };

  const handleProposeRepair = async (findingId: number) => {
    setProposingRepair(findingId);
    setRepairSuccessNotice(null);
    try {
      const proposal = await proposeRepair(findingId);
      setRepairSuccessNotice({
        id: proposal?.id || findingId,
        message: 'Minimal repair patch generated successfully!'
      });
    } catch (err) {
      console.error(err);
      alert('Failed to create repair proposal.');
    } finally {
      setProposingRepair(null);
    }
  };


  if (loading) return <LoadingSpinner message="Loading verification results..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  // Get the latest run (either from direct run or from history)
  const displayRun = latestRun || (runs && runs.length > 0 ? runs[runs.length - 1] : null);
  const findings: VerificationFinding[] = displayRun?.findings || [];
  const filteredFindings = statusFilter === 'all' ? findings : findings.filter(f => f.status === statusFilter);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <ShieldCheck className="w-7 h-7 text-emerald-400" />
            Verification Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time graph reachability and formal ACL security policy audit.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsAutoPilotOpen(true)}
            className="flex items-center px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-md transition-all"
          >
            <Zap className="w-4 h-4 mr-1.5 fill-white" />
            Auto-Pilot Enforce
          </button>

          <button
            onClick={handleRunVerification}
            disabled={isRunning}
            className="flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <div className="w-3.5 h-3.5 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Auditing Mesh...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 mr-2 fill-white" />
                Run Verification
              </>
            )}
          </button>
        </div>
      </div>

      {/* Autonomous AI Self-Healing Quick Bar */}
      <div className="card p-5 bg-gradient-to-r from-slate-900 via-cyan-950/25 to-slate-900 border-cyan-500/30 shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Autonomous Requirement Auto-Enforcer
            </span>
          </div>
          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
            0-Step Manual Intervention
          </span>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-2.5">
          <input
            type="text"
            value={autoPilotPrompt}
            onChange={(e) => setAutoPilotPrompt(e.target.value)}
            placeholder="Type any plain English rule (e.g. 'Stop guest from reaching HR')..."
            className="w-full px-3.5 py-2 bg-slate-950 border border-slate-700/80 rounded-lg text-xs font-mono text-cyan-300 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
          />
          <button
            onClick={() => setIsAutoPilotOpen(true)}
            className="w-full sm:w-auto px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg shadow-sm transition-all flex items-center justify-center gap-1.5 flex-shrink-0"
          >
            <Zap className="w-3.5 h-3.5 fill-white" />
            🚀 Auto-Enforce
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 text-[11px] font-medium">Try instantly:</span>
          {["Stop guest from reaching HR", "Isolate database from guest", "Block all traffic between guest and HR"].map((ex, i) => (
            <button
              key={i}
              onClick={() => {
                setAutoPilotPrompt(ex);
                setIsAutoPilotOpen(true);
              }}
              className="text-[11px] px-2.5 py-0.5 rounded bg-slate-850 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-700 font-mono transition-colors"
            >
              "{ex}"
            </button>
          ))}
        </div>
      </div>


      {repairSuccessNotice && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-md shadow-emerald-500/10">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 flex-shrink-0 text-emerald-400" />
            <div>
              <div className="text-sm font-semibold">{repairSuccessNotice.message}</div>
              <div className="text-xs text-slate-400 font-mono">Proposal #{repairSuccessNotice.id} ready for sandbox validation and deployment.</div>
            </div>
          </div>
          <Link
            to="/repairs"
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
          >
            Review &amp; Apply in Repairs Center
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Summary bar */}

      {displayRun && (
        <div className="grid grid-cols-4 gap-4">
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-white">{displayRun.total_policies}</div>
            <div className="text-xs text-slate-400 mt-1">Total Policies</div>
          </div>
          <div className="card p-4 text-center border-l-2 border-emerald-500">
            <div className="text-2xl font-bold text-emerald-400">{displayRun.passed}</div>
            <div className="text-xs text-slate-400 mt-1">Passing</div>
          </div>
          <div className="card p-4 text-center border-l-2 border-red-500">
            <div className="text-2xl font-bold text-red-400">{displayRun.failed}</div>
            <div className="text-xs text-slate-400 mt-1">Failing</div>
          </div>
          <div className="card p-4 text-center border-l-2 border-amber-500">
            <div className="text-2xl font-bold text-amber-400">{displayRun.unknown}</div>
            <div className="text-xs text-slate-400 mt-1">Unknown</div>
          </div>
        </div>
      )}

      {/* Filter */}
      {findings.length > 0 && (
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-400">Filter:</span>
          {['all', 'PASS', 'FAIL', 'UNKNOWN'].map(f => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                statusFilter === f
                  ? f === 'PASS' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                    f === 'FAIL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                    f === 'UNKNOWN' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                    'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-500'
              }`}
            >
              {f === 'all' ? `All (${findings.length})` : `${f} (${findings.filter(ff => ff.status === f).length})`}
            </button>
          ))}
        </div>
      )}

      {/* Findings */}
      <div className="space-y-3">
        {!displayRun ? (
          <div className="card p-16 text-center">
            <ShieldCheck className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <div className="text-lg text-slate-400">No verification results yet</div>
            <p className="text-sm text-slate-500 mt-2">
              Create some intents first, then click "Run Verification" to check your network configuration against your policies.
            </p>
          </div>
        ) : filteredFindings.length === 0 ? (
          <div className="card p-8 text-center text-slate-500">
            No findings matching the current filter.
          </div>
        ) : (
          filteredFindings.map((finding) => (
            <div key={finding.id} className={`card overflow-hidden border-l-4 ${
              finding.status === 'PASS' ? 'border-l-emerald-500' :
              finding.status === 'FAIL' ? 'border-l-red-500' : 'border-l-amber-500'
            }`}>
              <div 
                className="p-4 flex justify-between items-start cursor-pointer hover:bg-slate-800/50 transition-colors"
                onClick={() => setExpandedFinding(expandedFinding === finding.id ? null : finding.id)}
              >
                <div className="flex items-start space-x-3 flex-1">
                  {finding.status === 'PASS' ? <CheckCircle className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" /> :
                   finding.status === 'FAIL' ? <ShieldAlert className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" /> :
                   <HelpCircle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <div className="text-white font-medium">
                      {finding.details || `Policy #${finding.policy_id} verification`}
                    </div>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                        finding.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400' :
                        finding.status === 'FAIL' ? 'bg-red-500/10 text-red-400' :
                        'bg-amber-500/10 text-amber-400'
                      }`}>
                        {finding.status}
                      </span>
                      {finding.severity && (
                        <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                          finding.severity === 'critical' ? 'bg-red-500/10 text-red-300' :
                          finding.severity === 'high' ? 'bg-orange-500/10 text-orange-300' :
                          finding.severity === 'medium' ? 'bg-amber-500/10 text-amber-300' :
                          'bg-slate-700 text-slate-300'
                        }`}>
                          {finding.severity.toUpperCase()}
                        </span>
                      )}
                      {finding.affected_devices && finding.affected_devices.length > 0 && (
                        <span className="text-xs text-slate-500">
                          Devices: {finding.affected_devices.join(', ')}
                        </span>
                      )}
                    </div>
                  </div>
                  {expandedFinding === finding.id ? 
                    <ChevronDown className="w-5 h-5 text-slate-500 flex-shrink-0" /> : 
                    <ChevronRight className="w-5 h-5 text-slate-500 flex-shrink-0" />
                  }
                </div>
                <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                  {finding.status === 'FAIL' && (
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleProposeRepair(finding.id); }}
                      disabled={proposingRepair === finding.id}
                      className="flex items-center px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 rounded border border-amber-500/30 text-sm transition-colors disabled:opacity-50"
                    >
                      <Wrench className="w-3.5 h-3.5 mr-1.5" />
                      {proposingRepair === finding.id ? 'Creating...' : 'Propose Repair'}
                    </button>
                  )}
                </div>
              </div>

              {/* Expanded evidence section */}
              {expandedFinding === finding.id && (
                <div className="p-4 bg-slate-900/50 border-t border-slate-700 space-y-4">
                  {finding.remediation && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">Recommended Remediation</h4>
                      <p className="text-sm text-amber-300">{finding.remediation}</p>
                    </div>
                  )}
                  {finding.affected_networks && finding.affected_networks.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">Affected Networks</h4>
                      <div className="flex flex-wrap gap-1">
                        {finding.affected_networks.map((net, i) => (
                          <span key={i} className="px-2 py-0.5 text-xs bg-slate-800 text-slate-300 rounded font-mono">
                            {net}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {finding.evidence && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">Evidence</h4>
                      <pre className="text-xs text-slate-300 bg-slate-950 p-3 rounded overflow-x-auto font-mono">
                        {JSON.stringify(finding.evidence, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Verification history */}
      {runs && runs.length > 1 && (
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-3">Previous Runs</h3>
          <div className="space-y-2">
            {runs.slice(0, -1).reverse().map((run: VerificationRun) => (
              <div
                key={run.id}
                className="flex items-center justify-between p-2 rounded bg-slate-800/50 hover:bg-slate-800 cursor-pointer transition-colors"
                onClick={() => setLatestRun(run)}
              >
                <span className="text-sm text-slate-300">
                  Run #{run.id} · {new Date(run.started_at).toLocaleString()}
                </span>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-emerald-400">{run.passed} pass</span>
                  <span className="text-red-400">{run.failed} fail</span>
                  <span className="text-amber-400">{run.unknown} unknown</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Autonomous AutoPilot Modal */}
      <AutoPilotModal
        isOpen={isAutoPilotOpen}
        onClose={() => setIsAutoPilotOpen(false)}
        defaultPrompt={autoPilotPrompt}
        onSuccess={() => {
          refetch();
        }}
      />
    </div>
  );
};

