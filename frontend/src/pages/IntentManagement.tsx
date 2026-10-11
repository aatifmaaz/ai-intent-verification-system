import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getIntents, createIntent, deleteIntent } from '../api/intents';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Plus, Trash2, ChevronDown, ChevronRight, MessageSquare } from 'lucide-react';
import { Intent, NormalizedPolicy } from '../types';

const EXAMPLE_INTENTS = [
  "The HR network must not communicate with the guest network.",
  "All devices in the engineering network must be able to access the internal application server.",
  "Only administrators may access network devices using SSH.",
  "Guest devices must have internet access but must not access internal servers.",
  "The backup network must remain isolated from ordinary user traffic.",
];

export const IntentManagement = () => {
  const { data: intents, loading, error, refetch } = useApi(getIntents);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [newIntentText, setNewIntentText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIntentText.trim()) return;
    
    setSubmitting(true);
    try {
      await createIntent(newIntentText);
      setNewIntentText('');
      setIsFormOpen(false);
      refetch();
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
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

  if (loading) return <LoadingSpinner message="Loading intents..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Intent Management</h1>
        <button
          onClick={() => setIsFormOpen(!isFormOpen)}
          className="flex items-center px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-md transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Intent
        </button>
      </div>

      {isFormOpen && (
        <div className="card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Natural Language Intent</label>
              <textarea
                value={newIntentText}
                onChange={(e) => setNewIntentText(e.target.value)}
                placeholder="Describe the network behavior you want to enforce..."
                className="w-full h-28 px-4 py-3 bg-slate-900 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono text-sm"
              />
            </div>
            {/* Example intents */}
            <div>
              <p className="text-xs text-slate-500 mb-2">Try an example:</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_INTENTS.map((ex, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setNewIntentText(ex)}
                    className="text-xs px-2 py-1 bg-slate-800 text-slate-400 rounded hover:bg-slate-700 hover:text-slate-200 transition-colors truncate max-w-xs"
                    title={ex}
                  >
                    {ex.length > 50 ? ex.substring(0, 50) + '...' : ex}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setIsFormOpen(false)}
                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !newIntentText.trim()}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-md transition-colors disabled:opacity-50"
              >
                {submitting ? 'Processing...' : 'Submit Intent'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-4">
        {(intents || []).length === 0 ? (
          <div className="text-center py-16">
            <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 text-lg">No intents defined yet</p>
            <p className="text-slate-500 text-sm mt-1">Click "New Intent" to define your first network policy</p>
          </div>
        ) : (
          (intents || []).map((intent: Intent) => (
            <div key={intent.id} className="card overflow-hidden">
              <div 
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/50 transition-colors"
                onClick={() => setExpandedId(expandedId === intent.id ? null : intent.id)}
              >
                <div className="flex items-center space-x-4 flex-1 min-w-0">
                  {expandedId === intent.id ? <ChevronDown className="w-5 h-5 text-slate-500 flex-shrink-0" /> : <ChevronRight className="w-5 h-5 text-slate-500 flex-shrink-0" />}
                  <div className="min-w-0 flex-1">
                    <div className="text-white font-medium truncate">{intent.natural_language}</div>
                    <div className="text-sm text-slate-500 mt-0.5">
                      Confidence: {intent.confidence ? `${(intent.confidence * 100).toFixed(0)}%` : 'N/A'} · 
                      {intent.policies?.length || 0} {intent.policies?.length === 1 ? 'policy' : 'policies'}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-4 flex-shrink-0">
                  <span className={`px-2 py-1 text-xs rounded-full font-medium ${
                    intent.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                    intent.status === 'parsed' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' :
                    intent.status === 'draft' ? 'bg-slate-700 text-slate-300 border border-slate-600' :
                    'bg-slate-700 text-slate-400 border border-slate-600'
                  }`}>
                    {intent.status.toUpperCase()}
                  </span>
                  <button onClick={(e) => handleDelete(intent.id, e)} className="p-2 text-slate-500 hover:text-red-400 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {expandedId === intent.id && (
                <div className="p-4 bg-slate-900/50 border-t border-slate-700">
                  <h4 className="text-sm font-semibold text-slate-400 mb-3">Normalized Policies</h4>
                  {(!intent.policies || intent.policies.length === 0) ? (
                    <p className="text-slate-500 text-sm">No policies generated. Intent could not be parsed.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left">
                        <thead className="text-xs text-slate-400 uppercase bg-slate-800/50">
                          <tr>
                            <th className="px-4 py-2 rounded-tl-lg">Type</th>
                            <th className="px-4 py-2">Source</th>
                            <th className="px-4 py-2">Destination</th>
                            <th className="px-4 py-2">Protocol</th>
                            <th className="px-4 py-2">Port</th>
                            <th className="px-4 py-2 rounded-tr-lg">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {intent.policies.map((policy: NormalizedPolicy) => (
                            <tr key={policy.id} className="border-b border-slate-800 font-mono text-slate-300">
                              <td className="px-4 py-3">
                                <span className={`px-2 py-0.5 text-xs rounded ${
                                  policy.policy_type === 'deny' ? 'bg-red-500/10 text-red-400' :
                                  policy.policy_type === 'allow' ? 'bg-emerald-500/10 text-emerald-400' :
                                  policy.policy_type === 'isolate' ? 'bg-amber-500/10 text-amber-400' :
                                  'bg-blue-500/10 text-blue-400'
                                }`}>
                                  {policy.policy_type}
                                </span>
                              </td>
                              <td className="px-4 py-3">{policy.source_zone || policy.source_network || '—'}</td>
                              <td className="px-4 py-3">{policy.destination_zone || policy.destination_network || '—'}</td>
                              <td className="px-4 py-3">{policy.protocol || 'any'}</td>
                              <td className="px-4 py-3">{policy.port || 'any'}</td>
                              <td className="px-4 py-3">
                                <span className={policy.action === 'permit' ? 'text-emerald-400' : 'text-red-400'}>
                                  {policy.action}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
