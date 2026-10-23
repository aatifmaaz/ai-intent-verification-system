import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { getDashboardStats, getRecentActivity, getVerificationHistory } from '../api/dashboard';
import { MetricCard } from '../components/common/MetricCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Server, Shield, CheckCircle, AlertTriangle, HelpCircle, Wrench, Zap, Sparkles } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { AutoPilotModal } from '../components/AutoPilotModal';
import { getTopologySuggestions, type TopologySuggestions } from '../api/topology';

export const Dashboard = () => {
  const { data: stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useApi(getDashboardStats);
  const { data: activity, loading: activityLoading } = useApi(() => getRecentActivity(10));
  const { data: history, loading: historyLoading } = useApi(getVerificationHistory);

  const [isAutoPilotOpen, setIsAutoPilotOpen] = useState(false);
  const [heroPrompt, setHeroPrompt] = useState('Stop guest from reaching HR');
  const [suggestionsData, setSuggestionsData] = useState<TopologySuggestions | null>(null);

  useEffect(() => {
    getTopologySuggestions().then((data) => {
      setSuggestionsData(data);
      if (data?.suggestions && data.suggestions.length > 0) {
        setHeroPrompt(data.suggestions[0]);
      }
    }).catch(() => {});
  }, []);

  // Keep the dashboard mounted during background refreshes. The auto-pilot
  // modal owns its result state; unmounting it after enforcement hides the
  // successful run when onSuccess refreshes dashboard statistics.
  if (statsLoading && !stats) return <LoadingSpinner message="Loading dashboard statistics..." />;
  if (statsError) return <ErrorMessage message={statsError.message} onRetry={refetchStats} />;

  const PIE_COLORS = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6'];

  // Build trend data from verification history (latest 10 runs in chronological order)
  const trendData = (history?.runs || [])
    .slice(0, 10)
    .reverse()
    .map((run: { id: number; started_at: string; passed: number; failed: number; unknown: number }) => ({
      name: `${new Date(run.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${new Date(run.started_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`,
      pass: run.passed,
      fail: run.failed,
    }));

  // Build violations pie data from stats
  const violationsPie = stats ? [
    { name: 'Passing', value: stats.passed },
    { name: 'Violations', value: stats.failed },
    { name: 'Unknown', value: stats.unknown },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-6">
      {/* SIMULATED NETWORK VERIFICATION STUDIO HERO SECTION */}
      <div className="card p-6 bg-gradient-to-r from-slate-900 via-cyan-950/30 to-slate-900 border-cyan-500/40 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-500/20">
              <Zap className="w-6 h-6 fill-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">
                  Automated Network Verification Studio
                </h2>
                <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Closed-Loop Simulated Verification
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Define network requirements in natural language. The system translates intents into formal policies, verifies network graph reachability, isolates violations, validates patches in a sandbox, and applies changes to simulated device configurations with rollback support.
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsAutoPilotOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-cyan-600/30 transition-all flex-shrink-0"
          >
            <Sparkles className="w-4 h-4 fill-white" />
            Launch AI Studio
          </button>
        </div>

        {/* Inline Prompt Bar */}
        <div className="mt-4 flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <input
              type="text"
              value={heroPrompt}
              onChange={(e) => setHeroPrompt(e.target.value)}
              placeholder="e.g. Stop guest from reaching HR, or Isolate database from guest..."
              className="w-full px-4 py-2.5 bg-slate-950 border border-slate-700/80 rounded-lg text-xs font-mono text-cyan-300 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <button
            onClick={() => setIsAutoPilotOpen(true)}
            className="w-full sm:w-auto px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg shadow-md transition-all flex items-center justify-center gap-2 flex-shrink-0"
          >
            <Zap className="w-3.5 h-3.5 fill-white" />
            Auto-Enforce (1-Click)
          </button>
        </div>

        {/* Quick Clickable Suggestions */}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 font-semibold text-[11px]">
            Suggestions for {suggestionsData?.template_name || 'Network'}:
          </span>
          {(suggestionsData?.suggestions?.slice(0, 4) || [
            "Stop guest from reaching HR",
            "Isolate database from guest",
            "Block all traffic between guest and HR",
            "Prevent guest from accessing database"
          ]).map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                setHeroPrompt(item);
                setIsAutoPilotOpen(true);
              }}
              className="px-2.5 py-1 text-[11px] rounded bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-700/60 transition-colors font-mono"
            >
              "{item}"
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Network Telemetry &amp; Metrics</h1>
        <span className="text-xs text-slate-400 font-mono">{stats?.total_devices ?? 0} Devices Online</span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricCard title="Total Devices" value={stats?.total_devices || 0} icon={Server} color="cyan" />
        <MetricCard title="Active Policies" value={stats?.total_policies || 0} icon={Shield} color="cyan" />
        <MetricCard title="Passing" value={stats?.passed || 0} icon={CheckCircle} color="emerald" />
        <MetricCard title="Violations" value={stats?.failed || 0} icon={AlertTriangle} color="red" />
        <MetricCard title="Unknown" value={stats?.unknown || 0} icon={HelpCircle} color="amber" />
        <MetricCard title="Pending Repairs" value={stats?.pending_repairs || 0} icon={Wrench} color="amber" />
      </div>

      {/* Quick Launchpad */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <a
          href="/verification"
          className="card p-3.5 hover:border-cyan-500/50 transition-all flex items-center gap-3 group"
        >
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 group-hover:scale-110 transition-transform">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-bold text-white group-hover:text-cyan-400 transition-colors">Run Verification</div>
            <div className="text-[11px] text-slate-400">Verify graph reachability</div>
          </div>
        </a>

        <a
          href="/repairs"
          className="card p-3.5 hover:border-amber-500/50 transition-all flex items-center gap-3 group"
        >
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 group-hover:scale-110 transition-transform">
            <Wrench className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-bold text-white group-hover:text-amber-400 transition-colors">Repair Center</div>
            <div className="text-[11px] text-slate-400">Review &amp; apply patches</div>
          </div>
        </a>

        <a
          href="/simulation"
          className="card p-3.5 hover:border-purple-500/50 transition-all flex items-center gap-3 group"
        >
          <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 group-hover:scale-110 transition-transform">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-bold text-white group-hover:text-purple-400 transition-colors">Simulation Lab</div>
            <div className="text-[11px] text-slate-400">Test Scenarios A - E</div>
          </div>
        </a>

        <a
          href="/configurations"
          className="card p-3.5 hover:border-blue-500/50 transition-all flex items-center gap-3 group"
        >
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 group-hover:scale-110 transition-transform">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-bold text-white group-hover:text-blue-400 transition-colors">Device Configs</div>
            <div className="text-[11px] text-slate-400">Inspect &amp; validate syntax</div>
          </div>
        </a>
      </div>


      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="card p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">Verification Trends</h2>
          {historyLoading ? <LoadingSpinner /> : trendData.length === 0 ? (
            <div className="h-72 flex items-center justify-center text-slate-500">
              No verification history yet. Run a verification to see trends.
            </div>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                  <Line type="monotone" dataKey="pass" stroke="#10b981" strokeWidth={2} name="Passing" dot={{ fill: '#10b981' }} />
                  <Line type="monotone" dataKey="fail" stroke="#ef4444" strokeWidth={2} name="Failing" dot={{ fill: '#ef4444' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4">Policy Status</h2>
          {violationsPie.length === 0 ? (
            <div className="h-72 flex items-center justify-center text-slate-500 text-sm">
              No verification data yet
            </div>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={violationsPie} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={5} dataKey="value" label>
                    {violationsPie.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                  <Legend wrapperStyle={{ color: '#94a3b8' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        {activityLoading ? <LoadingSpinner /> : !activity || activity.length === 0 ? (
          <div className="text-slate-500 text-sm py-4 text-center">No recent activity</div>
        ) : (
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {activity.map((event: { id: number; event_type: string; description: string; created_at: string }) => (
              <div key={event.id} className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                  event.event_type.includes('repair') ? 'bg-amber-400' :
                  event.event_type.includes('verification') ? 'bg-cyan-400' :
                  event.event_type.includes('intent') ? 'bg-blue-400' : 'bg-slate-400'
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200">{event.description}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(event.created_at).toLocaleString()} · <span className="text-slate-400">{event.event_type}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Autonomous AutoPilot Modal */}
      <AutoPilotModal
        isOpen={isAutoPilotOpen}
        onClose={() => setIsAutoPilotOpen(false)}
        defaultPrompt={heroPrompt}
        onSuccess={() => {
          refetchStats();
          getTopologySuggestions().then(setSuggestionsData).catch(() => {});
        }}
      />
    </div>
  );
};

