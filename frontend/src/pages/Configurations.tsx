import React, { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { getTopology } from '../api/topology';
import { getDeviceConfigurations, importConfiguration, validateConfiguration } from '../api/configurations';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Device, DeviceConfigDetail } from '../types';
import { 
  FileCode, 
  CheckCircle, 
  AlertCircle, 
  History, 
  Code, 
  Upload, 
  Copy, 
  Check, 
  Layers, 
  Route, 
  ShieldAlert,
  Server,
  Terminal,
  Cpu
} from 'lucide-react';

const SAMPLE_CONFIGS: Record<string, { format: 'ios' | 'json' | 'yaml'; content: string }> = {
  cisco_acl: {
    format: 'ios',
    content: `hostname edge-firewall-01
!
interface GigabitEthernet0/0
 ip address 10.0.1.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 ip address 192.168.1.1 255.255.255.0
 no shutdown
!
ip route 10.1.0.0 255.255.0.0 10.0.1.254
!
ip access-list extended guest-restrict
 deny ip 192.168.1.0 0.0.0.255 10.0.1.0 0.0.0.255
 permit tcp 192.168.1.0 0.0.0.255 any eq 443
 permit tcp 192.168.1.0 0.0.0.255 any eq 80
 deny ip any any
!`
  },
  json_router: {
    format: 'json',
    content: `{
  "hostname": "core-router-01",
  "interfaces": [
    { "name": "GigabitEthernet0/0", "ip_address": "10.0.0.1", "subnet_mask": "255.255.255.0", "status": "up" },
    { "name": "GigabitEthernet0/1", "ip_address": "10.0.1.2", "subnet_mask": "255.255.255.0", "status": "up" }
  ],
  "routes": [
    { "network": "10.1.10.0", "mask": "255.255.255.0", "next_hop": "10.0.3.1" },
    { "network": "10.1.20.0", "mask": "255.255.255.0", "next_hop": "10.0.3.1" }
  ],
  "acls": [
    {
      "name": "management-plane-protect",
      "rules": [
        { "action": "permit", "protocol": "tcp", "source": "10.1.40.0/24", "destination": "any", "port": 22 },
        { "action": "deny", "protocol": "tcp", "source": "any", "destination": "any", "port": 22 },
        { "action": "permit", "protocol": "ip", "source": "any", "destination": "any", "port": "any" }
      ]
    }
  ]
}`
  },
  yaml_switch: {
    format: 'yaml',
    content: `hostname: dist-switch-01
vlans:
  - id: 10
    name: engineering
  - id: 20
    name: human_resources
  - id: 30
    name: guest_wifi
interfaces:
  - name: GigabitEthernet1/0/1
    vlan: 10
    status: up
  - name: GigabitEthernet1/0/2
    vlan: 20
    status: up
acls:
  - name: vlan-isolation
    rules:
      - action: deny
        protocol: ip
        source: 192.168.1.0/24
        destination: 10.0.1.0/24
`
  }
};

export const Configurations: React.FC = () => {
  const { data: topologyData, loading: topLoading, error: topError, refetch: refetchTopology } = useApi(getTopology);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [deviceDetail, setDeviceDetail] = useState<DeviceConfigDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'raw' | 'parsed' | 'import' | 'history'>('raw');

  // Import form state
  const [importFormat, setImportFormat] = useState<'ios' | 'json' | 'yaml'>('ios');
  const [importContent, setImportContent] = useState('');
  const [validationResult, setValidationResult] = useState<{ valid: boolean; message: string; parsed?: Record<string, unknown> } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Set default selected device once topology loads
  useEffect(() => {
    if (topologyData?.devices && topologyData.devices.length > 0 && !selectedDevice) {
      setSelectedDevice(topologyData.devices[0]);
    }
  }, [topologyData, selectedDevice]);

  // Load device config details when device changes
  useEffect(() => {
    if (!selectedDevice) return;
    let isMounted = true;
    setDetailLoading(true);
    setValidationResult(null);
    setActionSuccess(null);

    getDeviceConfigurations(selectedDevice.id)
      .then((detail) => {
        if (isMounted) {
          setDeviceDetail(detail);
          setDetailLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load device config:', err);
        if (isMounted) setDetailLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedDevice]);

  const handleValidate = async () => {
    if (!importContent.trim()) {
      setValidationResult({ valid: false, message: 'Configuration content cannot be empty' });
      return;
    }
    try {
      const res = await validateConfiguration(importFormat, importContent);
      setValidationResult({
        valid: res.valid,
        message: res.message,
        parsed: res.parsed
      });
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Validation failed';
      setValidationResult({
        valid: false,
        message: `Validation request error: ${errorMsg}`
      });
    }
  };

  const handleSaveConfig = async () => {
    if (!selectedDevice) return;
    setIsSubmitting(true);
    setActionSuccess(null);
    try {
      await importConfiguration(selectedDevice.id, importFormat, importContent);
      setActionSuccess(`Configuration successfully saved and committed to ${selectedDevice.name}!`);
      // Refresh details
      const updated = await getDeviceConfigurations(selectedDevice.id);
      setDeviceDetail(updated);
      refetchTopology();
      setActiveTab('parsed');
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to import configuration';
      alert(`Error saving configuration: ${errorMsg}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const loadSample = (key: string) => {
    const sample = SAMPLE_CONFIGS[key];
    if (sample) {
      setImportFormat(sample.format);
      setImportContent(sample.content);
      setValidationResult(null);
    }
  };

  if (topLoading) return <LoadingSpinner message="Loading network devices and configurations..." />;
  if (topError) return <ErrorMessage message={topError.message} onRetry={refetchTopology} />;

  const devices = topologyData?.devices || [];
  const currentConfigData = (deviceDetail?.current_config || selectedDevice?.config || {}) as Record<string, unknown>;
  const activeConfig = deviceDetail?.active_configuration;

  const acls = (currentConfigData.acls as Array<{ name: string; rules: Array<{ action: string; protocol: string; source: string; destination: string; port: string | number }> }>) || [];
  const routes = (currentConfigData.routes as Array<{ network: string; mask: string; next_hop: string }>) || [];
  const interfaces = (currentConfigData.interfaces as Array<{ name: string; ip_address?: string; status?: string }>) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FileCode className="w-7 h-7 text-cyan-400" />
            Device Configuration Management
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Inspect, validate, and deploy multi-vendor configurations (Cisco IOS, JSON, YAML) with automated version tracking
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setActiveTab('import');
              setImportFormat('ios');
              setImportContent(SAMPLE_CONFIGS.cisco_acl.content);
            }}
            className="flex items-center gap-2 px-3.5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-cyan-600/20"
          >
            <Upload className="w-4 h-4" />
            Import Configuration
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm font-medium">{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-white text-xs">Dismiss</button>
        </div>
      )}

      {/* Main Grid: Device List on Left, Config Workspace on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Device Selector */}
        <div className="lg:col-span-1 space-y-3">
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Monitored Devices</h2>
              <span className="text-xs bg-slate-800 text-cyan-400 px-2 py-0.5 rounded-full font-mono">{devices.length}</span>
            </div>
            <div className="space-y-1.5 max-h-[600px] overflow-y-auto pr-1">
              {devices.map((dev) => {
                const isSelected = selectedDevice?.id === dev.id;
                return (
                  <button
                    key={dev.id}
                    onClick={() => setSelectedDevice(dev)}
                    className={`w-full text-left p-3 rounded-lg border transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/20'
                        : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800 text-slate-300 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className={`w-2 h-2 rounded-full ${dev.status === 'active' ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{dev.name}</div>
                        <div className="text-xs text-slate-500 font-mono truncate">{dev.ip_address}</div>
                      </div>
                    </div>
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700">
                      {dev.device_type}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quick Info Card */}
          {selectedDevice && (
            <div className="card p-4 space-y-3">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <Server className="w-3.5 h-3.5 text-cyan-400" />
                Device Profile
              </h3>
              <div className="text-xs space-y-1.5 font-mono text-slate-300">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-500">Zone:</span>
                  <span className="text-cyan-400 font-medium">{selectedDevice.zone || 'Global'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-500">Subnet:</span>
                  <span>{selectedDevice.subnet || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-500">VLAN:</span>
                  <span>{selectedDevice.vlan_id ?? 'Untagged'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Active Version:</span>
                  <span className="text-emerald-400 font-semibold">
                    v{activeConfig?.version || 1}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Configuration Workspace */}
        <div className="lg:col-span-3 space-y-4">
          {/* Tabs */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('raw')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  activeTab === 'raw'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Code className="w-4 h-4" />
                Raw Configuration
              </button>
              <button
                onClick={() => setActiveTab('parsed')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  activeTab === 'parsed'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Layers className="w-4 h-4" />
                Structured Rules
              </button>
              <button
                onClick={() => setActiveTab('import')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  activeTab === 'import'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Upload className="w-4 h-4" />
                Config Editor & Validator
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  activeTab === 'history'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <History className="w-4 h-4" />
                Revision History
              </button>
            </div>

            {activeTab === 'raw' && (
              <button
                onClick={() => copyToClipboard(activeConfig?.raw_content || JSON.stringify(currentConfigData, null, 2))}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            )}
          </div>

          {detailLoading ? (
            <div className="card p-12 flex justify-center">
              <LoadingSpinner message="Loading configuration for device..." />
            </div>
          ) : (
            <>
              {/* TAB 1: RAW CONFIG */}
              {activeTab === 'raw' && (
                <div className="card p-5 space-y-4">
                  <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800">
                    <span className="flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-cyan-400" />
                      Active Format: <strong className="text-white uppercase font-mono">{activeConfig?.format || 'JSON'}</strong>
                    </span>
                    <span>Last Updated: {activeConfig?.created_at ? new Date(activeConfig.created_at).toLocaleString() : 'System Seed'}</span>
                  </div>

                  <pre className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-cyan-300 font-mono text-xs overflow-x-auto leading-relaxed max-h-[520px]">
                    <code>
                      {activeConfig?.raw_content || JSON.stringify(currentConfigData, null, 2)}
                    </code>
                  </pre>
                </div>
              )}

              {/* TAB 2: STRUCTURED RULES */}
              {activeTab === 'parsed' && (
                <div className="space-y-4">
                  {/* ACLs Section */}
                  <div className="card p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-cyan-400" />
                        Access Control Lists (ACLs)
                      </h3>
                      <span className="text-xs text-slate-400 font-mono">{acls.length} ACL list(s)</span>
                    </div>

                    {acls.length === 0 ? (
                      <div className="text-xs text-slate-500 py-4 text-center">No explicit ACL rules configured on this device.</div>
                    ) : (
                      <div className="space-y-3">
                        {acls.map((acl, i) => (
                          <div key={i} className="p-3 bg-slate-900/60 rounded-lg border border-slate-800 space-y-2">
                            <div className="text-xs font-mono font-bold text-cyan-400 flex items-center justify-between">
                              <span>ACL: {acl.name}</span>
                              <span className="text-[10px] text-slate-400 font-normal">{acl.rules.length} rule(s)</span>
                            </div>
                            <div className="space-y-1">
                              {acl.rules.map((rule, ri) => (
                                <div key={ri} className="flex items-center justify-between p-2 rounded bg-slate-950/50 border border-slate-800/80 text-xs font-mono">
                                  <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                      rule.action === 'permit' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'
                                    }`}>
                                      {rule.action}
                                    </span>
                                    <span className="text-slate-400 font-semibold">{rule.protocol.toUpperCase()}</span>
                                  </div>
                                  <div className="text-slate-300">
                                    <span className="text-slate-500">src: </span>{rule.source}
                                    <span className="text-slate-500 ml-2">dst: </span>{rule.destination}
                                    <span className="text-slate-500 ml-2">port: </span>
                                    <span className="text-cyan-400">{String(rule.port)}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Routing Table & Interfaces in 2 Columns */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Routes */}
                    <div className="card p-5 space-y-3">
                      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                        <Route className="w-4 h-4 text-cyan-400" />
                        Static Routes
                      </h3>
                      {routes.length === 0 ? (
                        <div className="text-xs text-slate-500 py-4 text-center">No static routes configured</div>
                      ) : (
                        <div className="space-y-1.5 max-h-56 overflow-y-auto">
                          {routes.map((r, ri) => (
                            <div key={ri} className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono flex items-center justify-between">
                              <div>
                                <span className="text-slate-200 font-semibold">{r.network}</span>
                                <span className="text-slate-500 text-[10px] block">{r.mask}</span>
                              </div>
                              <div className="text-right">
                                <span className="text-slate-500 text-[10px]">next hop</span>
                                <span className="text-cyan-400 font-medium block">{r.next_hop}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Interfaces */}
                    <div className="card p-5 space-y-3">
                      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-cyan-400" />
                        Interfaces
                      </h3>
                      {interfaces.length === 0 ? (
                        <div className="text-xs text-slate-500 py-4 text-center">No interfaces mapped</div>
                      ) : (
                        <div className="space-y-1.5 max-h-56 overflow-y-auto">
                          {interfaces.map((intf, ii) => (
                            <div key={ii} className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-xs font-mono flex items-center justify-between">
                              <span className="text-slate-200 font-medium">{intf.name}</span>
                              <div className="flex items-center gap-2">
                                <span className="text-cyan-400">{intf.ip_address || 'Unassigned'}</span>
                                <span className={`w-1.5 h-1.5 rounded-full ${intf.status === 'down' ? 'bg-red-400' : 'bg-emerald-400'}`} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: IMPORT & VALIDATOR */}
              {activeTab === 'import' && (
                <div className="card p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-800">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Configuration Importer & Live Validator</h3>
                      <p className="text-xs text-slate-400">Validate syntactical compliance before committing to simulated device configuration</p>
                    </div>

                    {/* Presets */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">Presets:</span>
                      <button
                        onClick={() => loadSample('cisco_acl')}
                        className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded border border-slate-700"
                      >
                        Cisco IOS ACL
                      </button>
                      <button
                        onClick={() => loadSample('json_router')}
                        className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded border border-slate-700"
                      >
                        JSON Router
                      </button>
                      <button
                        onClick={() => loadSample('yaml_switch')}
                        className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded border border-slate-700"
                      >
                        YAML Switch
                      </button>
                    </div>
                  </div>

                  {/* Format Selector */}
                  <div className="flex items-center gap-4">
                    <span className="text-xs font-medium text-slate-300">Target Format:</span>
                    {(['ios', 'json', 'yaml'] as const).map((fmt) => (
                      <label key={fmt} className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                        <input
                          type="radio"
                          name="format"
                          value={fmt}
                          checked={importFormat === fmt}
                          onChange={() => setImportFormat(fmt)}
                          className="text-cyan-500 focus:ring-cyan-500"
                        />
                        <span className="uppercase font-mono">{fmt}</span>
                      </label>
                    ))}
                  </div>

                  {/* Code Editor Area */}
                  <div>
                    <textarea
                      value={importContent}
                      onChange={(e) => {
                        setImportContent(e.target.value);
                        setValidationResult(null);
                      }}
                      placeholder={`Paste ${importFormat.toUpperCase()} formatted configuration here...`}
                      rows={12}
                      className="w-full p-4 bg-slate-950 font-mono text-xs text-cyan-300 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-500/60 leading-relaxed resize-y"
                    />
                  </div>

                  {/* Validation Output Banner */}
                  {validationResult && (
                    <div className={`p-3.5 rounded-xl border flex items-start gap-3 ${
                      validationResult.valid 
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : 'bg-red-500/10 border-red-500/30 text-red-300'
                    }`}>
                      {validationResult.valid ? (
                        <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="text-xs space-y-1">
                        <div className="font-semibold">{validationResult.message}</div>
                        {validationResult.parsed && (
                          <div className="text-[11px] text-slate-400">
                            Parsed elements: {Object.keys(validationResult.parsed).join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Controls */}
                  <div className="flex items-center justify-between pt-2">
                    <button
                      onClick={handleValidate}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition-colors"
                    >
                      Run Syntax Validator
                    </button>
                    <button
                      onClick={handleSaveConfig}
                      disabled={isSubmitting || !importContent.trim()}
                      className="flex items-center gap-2 px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-cyan-600/20 disabled:opacity-50 transition-all"
                    >
                      {isSubmitting ? 'Deploying...' : `Deploy to ${selectedDevice?.name || 'Device'}`}
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 4: REVISION HISTORY */}
              {activeTab === 'history' && (
                <div className="card p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <History className="w-4 h-4 text-cyan-400" />
                    Configuration Version Ledger
                  </h3>

                  {!deviceDetail?.versions || deviceDetail.versions.length === 0 ? (
                    <div className="text-xs text-slate-500 py-6 text-center">
                      No previous revisions recorded for this device yet.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {deviceDetail.versions.map((ver) => (
                        <div key={ver.id} className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                                Revision {ver.version_number}
                              </span>
                              <span className="text-xs font-medium text-slate-200">{ver.change_description}</span>
                            </div>
                            <div className="text-[11px] text-slate-500">
                              Committed on: {new Date(ver.created_at).toLocaleString()}
                            </div>
                          </div>
                          <button
                            onClick={() => {
                              setImportFormat('json');
                              setImportContent(JSON.stringify(ver.config_data, null, 2));
                              setActiveTab('import');
                            }}
                            className="text-xs text-cyan-400 hover:text-cyan-300 font-medium px-2 py-1 rounded bg-slate-800 hover:bg-slate-700"
                          >
                            Restore This Version
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
