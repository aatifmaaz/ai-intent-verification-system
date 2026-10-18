import React, { useState, useEffect } from 'react';
import { 
  X, 
  Layers, 
  FileJson, 
  PlusCircle, 
  CheckCircle, 
  RefreshCw, 
  AlertCircle, 
  Network, 
  Building2, 
  Cloud, 
  HeartPulse, 
  Landmark,
  ArrowRight
} from 'lucide-react';
import { 
  getTopologyTemplates, 
  loadTopologyTemplate, 
  importCustomTopology, 
  createDevice,
  TopologyTemplate 
} from '../api/topology';

interface TopologyManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTopologyChanged: () => void;
}

const TEMPLATE_ICONS: Record<string, React.FC<{ className?: string }>> = {
  enterprise: Building2,
  datacenter: Cloud,
  healthcare: HeartPulse,
  fintech: Landmark
};

const SAMPLE_CUSTOM_TOPOLOGY = {
  name: "Retail Store Branch & POS Mesh",
  devices: [
    { name: "branch-edge-router", device_type: "router", ip_address: "192.168.100.1", subnet: "192.168.100.0/24", zone: "wan" },
    { name: "store-firewall", device_type: "firewall", ip_address: "192.168.100.2", subnet: "192.168.100.0/24", zone: "security" },
    { name: "pos-terminal-01", device_type: "client", ip_address: "192.168.110.10", subnet: "192.168.110.0/24", zone: "pos" },
    { name: "pos-terminal-02", device_type: "client", ip_address: "192.168.110.11", subnet: "192.168.110.0/24", zone: "pos" },
    { name: "inventory-db", device_type: "server", ip_address: "192.168.120.5", subnet: "192.168.120.0/24", zone: "database" },
    { name: "customer-guest-wifi", device_type: "client", ip_address: "192.168.130.100", subnet: "192.168.130.0/24", zone: "guest" }
  ],
  links: [
    { source: "branch-edge-router", target: "store-firewall" },
    { source: "store-firewall", target: "pos-terminal-01" },
    { source: "store-firewall", target: "pos-terminal-02" },
    { source: "store-firewall", target: "inventory-db" },
    { source: "store-firewall", target: "customer-guest-wifi" }
  ],
  intents: [
    "Customer guest wifi must not communicate with the POS terminals.",
    "Customer guest wifi must remain isolated from the inventory database."
  ]
};

export const TopologyManagerModal: React.FC<TopologyManagerModalProps> = ({
  isOpen,
  onClose,
  onTopologyChanged
}) => {
  const [activeTab, setActiveTab] = useState<'templates' | 'import' | 'addDevice'>('templates');
  const [templates, setTemplates] = useState<TopologyTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('enterprise');
  
  // Custom JSON Import state
  const [jsonInput, setJsonInput] = useState<string>(JSON.stringify(SAMPLE_CUSTOM_TOPOLOGY, null, 2));

  // Add Device state
  const [deviceName, setDeviceName] = useState('');
  const [deviceType, setDeviceType] = useState<'router' | 'switch' | 'firewall' | 'server' | 'client'>('server');
  const [ipAddress, setIpAddress] = useState('10.1.90.10');
  const [subnet, setSubnet] = useState('10.1.90.0/24');
  const [zone, setZone] = useState('custom-zone');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setLoadingTemplates(true);
      getTopologyTemplates()
        .then((res) => {
          setTemplates(res);
          setLoadingTemplates(false);
        })
        .catch(() => {
          setLoadingTemplates(false);
        });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleLoadTemplate = async (templateId: string) => {
    setIsSubmitting(true);
    setStatusNotice(null);
    setErrorMessage(null);
    try {
      const res = await loadTopologyTemplate(templateId);
      setStatusNotice(res.message);
      onTopologyChanged();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to switch topology template';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleImportJson = async () => {
    setIsSubmitting(true);
    setStatusNotice(null);
    setErrorMessage(null);
    try {
      const parsed = JSON.parse(jsonInput);
      if (!parsed.devices || !Array.isArray(parsed.devices)) {
        throw new Error('Topology JSON must contain a "devices" array');
      }
      const res = await importCustomTopology(parsed);
      setStatusNotice(res.message);
      onTopologyChanged();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid JSON or failed to import topology';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deviceName.trim()) return;
    setIsSubmitting(true);
    setStatusNotice(null);
    setErrorMessage(null);
    try {
      await createDevice({
        name: deviceName.trim(),
        device_type: deviceType,
        ip_address: ipAddress.trim(),
        subnet: subnet.trim(),
        zone: zone.trim()
      });
      setStatusNotice(`Device "${deviceName}" successfully added to the active topology!`);
      onTopologyChanged();
      setDeviceName('');
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create device';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div 
        className="w-full max-w-4xl bg-slate-900 border border-cyan-500/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-scaleUp"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-5 bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-md shadow-cyan-500/20">
              <Network className="w-5 h-5 fill-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">
                  Topology Switcher &amp; Custom Network Studio
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Multi-Topology Agnostic
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Deploy complete pre-built enterprise networks, upload custom topology JSON files, or add new nodes on the fly.
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

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 px-6 pt-4 border-b border-slate-800 bg-slate-950/40">
          <button
            onClick={() => setActiveTab('templates')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
              activeTab === 'templates'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-4 h-4" />
            Production Network Templates ({templates.length || 4})
          </button>

          <button
            onClick={() => setActiveTab('import')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
              activeTab === 'import'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <FileJson className="w-4 h-4" />
            Import Custom Topology JSON
          </button>

          <button
            onClick={() => setActiveTab('addDevice')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
              activeTab === 'addDevice'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <PlusCircle className="w-4 h-4" />
            + Add Node / Device
          </button>
        </div>

        {/* Feedback Notices */}
        {statusNotice && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{statusNotice}</span>
          </div>
        )}

        {errorMessage && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4">
          {/* TAB 1: PRODUCTION TEMPLATES */}
          {activeTab === 'templates' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-400">
                Choose any pre-architected network topology below. Switching topologies automatically updates the live interactive graph, resets configurations, re-evaluates zero-trust reachability, and primes the AI Auto-Pilot.
              </div>

              {loadingTemplates ? (
                <div className="py-12 text-center text-slate-500 text-xs flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                  Loading topology blueprints...
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(templates.length > 0 ? templates : [
                    { id: 'enterprise', name: 'Enterprise Campus Network', description: 'Multi-tier corporate campus with edge routing, distribution switches, and department zones.', device_count: 15, link_count: 15, sample_intents: ['The guest network must not communicate with the HR network.'] },
                    { id: 'datacenter', name: 'Cloud Spine-Leaf Data Center', description: 'High-bandwidth BGP Clos fabric interconnecting Kubernetes compute clusters and DB tiers.', device_count: 13, link_count: 15, sample_intents: ['External traffic must not directly access the postgres cluster.'] },
                    { id: 'healthcare', name: 'Smart Hospital Zero-Trust Mesh', description: 'Critical care hospital network isolating IoT medical devices from EHR records and visitor Wi-Fi.', device_count: 11, link_count: 10, sample_intents: ['Visitor patient wifi must not communicate with the EHR database.'] },
                    { id: 'fintech', name: 'FinTech Banking Payment Perimeter', description: 'High-assurance PCI-DSS banking network isolating cardholder data, ATM switches, and SWIFT.', device_count: 11, link_count: 10, sample_intents: ['Payment API gateway must not communicate directly with the cardholder vault.'] }
                  ]).map((tpl) => {
                    const IconComp = TEMPLATE_ICONS[tpl.id] || Building2;
                    const isSelected = selectedTemplateId === tpl.id;

                    return (
                      <div
                        key={tpl.id}
                        onClick={() => setSelectedTemplateId(tpl.id)}
                        className={`p-4 rounded-xl border cursor-pointer transition-all space-y-3 ${
                          isSelected 
                            ? 'bg-cyan-950/25 border-cyan-500/60 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-500/30'
                            : 'bg-slate-950/50 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className={`p-2 rounded-lg ${isSelected ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-800 text-slate-400'}`}>
                              <IconComp className="w-5 h-5" />
                            </div>
                            <div>
                              <h3 className="text-sm font-bold text-white">{tpl.name}</h3>
                              <span className="text-[10px] font-mono text-cyan-300">
                                {tpl.device_count} devices &middot; {tpl.link_count} links
                              </span>
                            </div>
                          </div>

                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                            isSelected ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'bg-slate-800 text-slate-500'
                          }`}>
                            {tpl.id}
                          </span>
                        </div>

                        <p className="text-xs text-slate-400 leading-relaxed">
                          {tpl.description}
                        </p>

                        {tpl.sample_intents && tpl.sample_intents.length > 0 && (
                          <div className="p-2 rounded bg-slate-900/80 border border-slate-800 text-[11px] font-mono text-slate-300 truncate">
                            <span className="text-slate-500">Sample rule: </span>
                            "{tpl.sample_intents[0]}"
                          </div>
                        )}

                        <div className="pt-1 flex items-center justify-end">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleLoadTemplate(tpl.id);
                            }}
                            disabled={isSubmitting}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg shadow-sm transition-all disabled:opacity-50"
                          >
                            {isSubmitting && selectedTemplateId === tpl.id ? (
                              <>
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                Deploying Mesh...
                              </>
                            ) : (
                              <>
                                <span>Deploy This Topology</span>
                                <ArrowRight className="w-3 h-3" />
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: IMPORT CUSTOM JSON */}
          {activeTab === 'import' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  Paste or edit any custom network topology definition in JSON format below. The engine will ingest your devices, establish link interconnections, and perform verification immediately.
                </p>

                <button
                  onClick={() => setJsonInput(JSON.stringify(SAMPLE_CUSTOM_TOPOLOGY, null, 2))}
                  className="text-xs text-cyan-400 hover:underline font-mono"
                >
                  Load Sample Retail Mesh &rarr;
                </button>
              </div>

              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                rows={13}
                className="w-full p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs text-cyan-200 leading-relaxed focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />

              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-slate-500 font-mono">
                  Schema: {`{ "name": string, "devices": [...], "links": [...], "intents": [...] }`}
                </span>

                <button
                  onClick={handleImportJson}
                  disabled={isSubmitting || !jsonInput.trim()}
                  className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-md transition-all disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Ingesting Custom Topology...
                    </>
                  ) : (
                    <>
                      <FileJson className="w-3.5 h-3.5" />
                      🚀 Import &amp; Verify Custom Topology
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: ADD SINGLE NODE */}
          {activeTab === 'addDevice' && (
            <form onSubmit={handleAddDevice} className="space-y-4 max-w-xl mx-auto">
              <div className="p-3 bg-cyan-950/20 border border-cyan-500/30 rounded-xl text-xs text-cyan-300">
                Quickly insert a single new device into the active network topology. The graph visualizer and reachability engine will register it immediately.
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300 uppercase">Device Hostname</label>
                <input
                  type="text"
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                  placeholder="e.g. secondary-firewall, dev-worker-3, voip-server"
                  required
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300 uppercase">Device Type</label>
                  <select
                    value={deviceType}
                    onChange={(e) => setDeviceType(e.target.value as any)}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="router">Router</option>
                    <option value="switch">Switch</option>
                    <option value="firewall">Firewall</option>
                    <option value="server">Server</option>
                    <option value="client">Client Endpoint</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300 uppercase">Security Zone</label>
                  <input
                    type="text"
                    value={zone}
                    onChange={(e) => setZone(e.target.value)}
                    placeholder="e.g. dmz, hr, database, guest"
                    required
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300 uppercase">IP Address</label>
                  <input
                    type="text"
                    value={ipAddress}
                    onChange={(e) => setIpAddress(e.target.value)}
                    placeholder="e.g. 10.1.90.10"
                    required
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300 uppercase">Subnet CIDR</label>
                  <input
                    type="text"
                    value={subnet}
                    onChange={(e) => setSubnet(e.target.value)}
                    placeholder="e.g. 10.1.90.0/24"
                    required
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="pt-3 flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmitting || !deviceName.trim()}
                  className="flex items-center gap-2 px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg shadow-sm transition-all disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Adding Node...
                    </>
                  ) : (
                    <>
                      <PlusCircle className="w-3.5 h-3.5" />
                      Add Node to Active Mesh
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between">
          <div className="text-xs text-slate-500 font-mono flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Dynamic Graph Fabric Ready
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
