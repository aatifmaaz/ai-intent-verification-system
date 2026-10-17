import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getAuditLogs, getAuditEventTypes } from '../api/audit';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { AuditEvent } from '../types';
import { 
  ClipboardList, 
  Search, 
  Filter, 
  Download, 
  Calendar, 
  User, 
  Code, 
  X, 
  ShieldCheck, 
  Wrench, 
  FileCode, 
  MessageSquare,
  FlaskConical,
  RefreshCw
} from 'lucide-react';

export const Audit: React.FC = () => {
  const [selectedEventType, setSelectedEventType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [inspectEvent, setInspectEvent] = useState<AuditEvent | null>(null);

  const { data: logs, loading, error, refetch } = useApi(
    () => getAuditLogs(200, selectedEventType, searchQuery),
    [selectedEventType, searchQuery]
  );

  const { data: eventTypes } = useApi(getAuditEventTypes);

  const handleExportJson = () => {
    if (!logs) return;
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `niv_audit_logs_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getEventIcon = (type: string) => {
    if (type.includes('VERIFICATION')) return <ShieldCheck className="w-4 h-4 text-cyan-400" />;
    if (type.includes('REPAIR')) return <Wrench className="w-4 h-4 text-amber-400" />;
    if (type.includes('CONFIG')) return <FileCode className="w-4 h-4 text-blue-400" />;
    if (type.includes('INTENT')) return <MessageSquare className="w-4 h-4 text-emerald-400" />;
    if (type.includes('SCENARIO')) return <FlaskConical className="w-4 h-4 text-purple-400" />;
    return <ClipboardList className="w-4 h-4 text-slate-400" />;
  };

  if (loading && !logs) return <LoadingSpinner message="Loading governance audit logs..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  const auditEvents = logs || [];
  const types = ['ALL', ...(eventTypes || [])];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <ClipboardList className="w-7 h-7 text-cyan-400" />
            Audit Trail & Governance Ledger
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable chronological record of policy creations, configuration imports, verification runs, and repair approvals
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button
            onClick={handleExportJson}
            disabled={auditEvents.length === 0}
            className="flex items-center gap-2 px-3.5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow-md shadow-cyan-600/20 disabled:opacity-50 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Export Audit Log (JSON)
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card p-4 space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search audit descriptions..."
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="text-xs text-slate-400 font-mono">
            Showing <strong className="text-white">{auditEvents.length}</strong> logged events
          </div>
        </div>

        {/* Type Filter Chips */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Filter className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
          {types.map((type) => (
            <button
              key={type}
              onClick={() => setSelectedEventType(type)}
              className={`px-2.5 py-1 text-xs rounded-lg font-mono uppercase whitespace-nowrap transition-colors ${
                selectedEventType === type
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 font-bold'
                  : 'text-slate-400 hover:text-white bg-slate-800/40 hover:bg-slate-800 border border-transparent'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Audit Log Timeline */}
      {auditEvents.length === 0 ? (
        <div className="card p-12 text-center text-slate-500 space-y-2">
          <ClipboardList className="w-8 h-8 mx-auto text-slate-600" />
          <p className="text-sm">No audit events match your filter criteria.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {auditEvents.map((evt) => (
            <div
              key={evt.id}
              className="card p-4 hover:border-slate-700 transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3.5 min-w-0">
                <div className="p-2 rounded-lg bg-slate-800 border border-slate-700 flex-shrink-0 mt-0.5">
                  {getEventIcon(evt.event_type)}
                </div>

                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-800 text-cyan-400 border border-slate-700">
                      {evt.event_type}
                    </span>
                    <span className="text-xs text-slate-500 font-mono flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(evt.created_at).toLocaleString()}
                    </span>
                    <span className="text-xs text-slate-500 font-mono flex items-center gap-1">
                      <User className="w-3 h-3" />
                      User #{evt.user_id || 'System'}
                    </span>
                  </div>

                  <p className="text-sm text-slate-200 font-medium leading-relaxed">
                    {evt.description}
                  </p>
                </div>
              </div>

              {evt.details && Object.keys(evt.details).length > 0 && (
                <button
                  onClick={() => setInspectEvent(evt)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-semibold rounded-lg border border-slate-700 transition-colors flex-shrink-0"
                >
                  <Code className="w-3.5 h-3.5" />
                  Inspect Payload
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* JSON Payload Inspection Modal */}
      {inspectEvent && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="card w-full max-w-2xl max-h-[80vh] flex flex-col border-cyan-500/40 shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Code className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">
                  Audit Event #{inspectEvent.id} Payload Detail
                </h3>
              </div>
              <button
                onClick={() => setInspectEvent(null)}
                className="text-slate-400 hover:text-white p-1 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-3">
              <div className="text-xs text-slate-400">
                <strong>Event:</strong> {inspectEvent.event_type} &middot;{' '}
                <strong>Timestamp:</strong> {new Date(inspectEvent.created_at).toLocaleString()}
              </div>

              <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-cyan-300 leading-relaxed overflow-x-auto">
                <code>{JSON.stringify(inspectEvent.details, null, 2)}</code>
              </pre>
            </div>

            <div className="p-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setInspectEvent(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
