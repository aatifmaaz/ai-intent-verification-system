import React, { useEffect, useRef, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getTopology } from '../api/topology';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Device, NetworkLink } from '../types';
import { 
  Network, 
  Search, 
  Filter, 
  RotateCcw, 
  Play, 
  Pause, 
  Server, 
  FileCode, 
  ExternalLink
} from 'lucide-react';
import { Link } from 'react-router-dom';


interface NodePos {
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  device: Device;
}

const TYPE_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  router: { bg: '#2563eb', border: '#60a5fa', glow: 'rgba(37, 99, 235, 0.4)' },
  switch: { bg: '#7c3aed', border: '#a78bfa', glow: 'rgba(124, 58, 237, 0.4)' },
  firewall: { bg: '#dc2626', border: '#f87171', glow: 'rgba(220, 38, 38, 0.4)' },
  server: { bg: '#059669', border: '#34d399', glow: 'rgba(5, 150, 105, 0.4)' },
  host: { bg: '#d97706', border: '#fbbf24', glow: 'rgba(217, 119, 6, 0.4)' },
  client: { bg: '#d97706', border: '#fbbf24', glow: 'rgba(217, 119, 6, 0.4)' },
};

export const Topology: React.FC = () => {
  const { data, loading, error, refetch } = useApi(getTopology);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [animatingTraffic, setAnimatingTraffic] = useState(true);
  
  const positionsRef = useRef<Map<number, NodePos>>(new Map());
  const animationFrameRef = useRef<number | null>(null);
  const pulseOffsetRef = useRef<number>(0);
  const draggingNodeRef = useRef<number | null>(null);

  // Initialize node layout based on hierarchical zones
  useEffect(() => {
    if (!data?.devices) return;

    const canvas = canvasRef.current;
    const width = canvas ? canvas.width : 840;
    const height = canvas ? canvas.height : 580;

    const zoneGroups: Record<string, Device[]> = {};
    data.devices.forEach((dev) => {
      const z = dev.zone || 'global';
      if (!zoneGroups[z]) zoneGroups[z] = [];
      zoneGroups[z].push(dev);
    });

    const newPositions = new Map<number, NodePos>();
    const centerX = width / 2;
    const centerY = height / 2;

    // Distribute zones in layers / circle
    const zoneKeys = Object.keys(zoneGroups);
    zoneKeys.forEach((zk, zIdx) => {
      const devs = zoneGroups[zk];
      const isCore = zk.toLowerCase().includes('core') || zk.toLowerCase().includes('edge');
      const baseRadius = isCore ? 90 : 190;
      const angleStep = (2 * Math.PI) / (zoneKeys.length || 1);
      const zoneBaseAngle = zIdx * angleStep;

      devs.forEach((dev, dIdx) => {
        const offset = (dIdx - (devs.length - 1) / 2) * 50;
        const angle = zoneBaseAngle + (offset / baseRadius);
        const radius = baseRadius + (dIdx % 2 === 0 ? 0 : 35);
        
        const x = Math.max(60, Math.min(width - 60, centerX + Math.cos(angle) * radius));
        const y = Math.max(60, Math.min(height - 60, centerY + Math.sin(angle) * radius));
        newPositions.set(dev.id, { x, y, device: dev });
      });
    });

    positionsRef.current = newPositions;
  }, [data]);

  // Main Canvas Render Loop with Traffic Pulse Animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let isRunning = true;

    const render = () => {
      if (!isRunning) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const positions = positionsRef.current;
      const links = data?.links || [];

      // Advance pulse offset for packet animation
      if (animatingTraffic) {
        pulseOffsetRef.current = (pulseOffsetRef.current + 0.015) % 1;
      }

      // Draw Links
      links.forEach((link: NetworkLink) => {
        const src = positions.get(link.source_device_id);
        const tgt = positions.get(link.target_device_id);
        if (!src || !tgt) return;

        // Check if either node matches current filters
        const srcMatches = zoneFilter === 'all' || src.device.zone === zoneFilter;
        const tgtMatches = zoneFilter === 'all' || tgt.device.zone === zoneFilter;
        const isDimmed = zoneFilter !== 'all' && !srcMatches && !tgtMatches;

        const isConnectedToSelected = selectedDevice && 
          (link.source_device_id === selectedDevice.id || link.target_device_id === selectedDevice.id);

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.strokeStyle = isConnectedToSelected 
          ? '#22d3ee' 
          : link.status === 'down'
          ? '#ef4444'
          : isDimmed 
          ? '#1e293b' 
          : '#334155';
        ctx.lineWidth = isConnectedToSelected ? 3 : 1.5;
        ctx.stroke();

        // Animate packets flowing along link
        if (animatingTraffic && link.status !== 'down' && !isDimmed) {
          const t = (pulseOffsetRef.current + (link.id * 0.17)) % 1;
          const px = src.x + (tgt.x - src.x) * t;
          const py = src.y + (tgt.y - src.y) * t;

          ctx.beginPath();
          ctx.arc(px, py, isConnectedToSelected ? 3.5 : 2.5, 0, 2 * Math.PI);
          ctx.fillStyle = isConnectedToSelected ? '#22d3ee' : '#38bdf8';
          ctx.shadowColor = '#38bdf8';
          ctx.shadowBlur = 6;
          ctx.fill();
          ctx.shadowBlur = 0; // reset
        }
      });

      // Draw Nodes
      positions.forEach(({ x, y, device }) => {
        const isSelected = selectedDevice?.id === device.id;
        const isMatchesZone = zoneFilter === 'all' || device.zone === zoneFilter;
        const isMatchesSearch = !searchQuery || 
          device.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          device.ip_address.includes(searchQuery);

        const isDimmed = !isMatchesZone || !isMatchesSearch;
        const colors = TYPE_COLORS[device.device_type] || TYPE_COLORS.router;

        // Outer glow on selected
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(x, y, 26, 0, 2 * Math.PI);
          ctx.fillStyle = 'rgba(34, 211, 238, 0.2)';
          ctx.fill();
          ctx.strokeStyle = '#22d3ee';
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Main Node Circle
        ctx.beginPath();
        ctx.arc(x, y, 18, 0, 2 * Math.PI);
        ctx.fillStyle = isDimmed ? '#1e293b' : colors.bg;
        ctx.fill();
        ctx.strokeStyle = isSelected ? '#22d3ee' : isDimmed ? '#334155' : colors.border;
        ctx.lineWidth = isSelected ? 2.5 : 1.5;
        ctx.stroke();

        // Status indicator dot
        ctx.beginPath();
        ctx.arc(x + 12, y - 12, 4.5, 0, 2 * Math.PI);
        ctx.fillStyle = device.status === 'active' ? '#10b981' : '#ef4444';
        ctx.fill();
        ctx.strokeStyle = '#0f172a';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Node Label
        ctx.font = isSelected ? 'bold 11px monospace' : '10px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = isSelected ? '#22d3ee' : isDimmed ? '#475569' : '#e2e8f0';
        ctx.fillText(device.name, x, y + 32);

        // Subnet / Zone
        if (!isDimmed) {
          ctx.font = '9px monospace';
          ctx.fillStyle = '#64748b';
          ctx.fillText(device.zone ? `[${device.zone}]` : device.ip_address, x, y + 44);
        }
      });

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      isRunning = false;
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [data, selectedDevice, zoneFilter, searchQuery, animatingTraffic]);

  // Canvas Mouse Interactions: Click to select, Drag to rearrange
  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    for (const [id, { x, y, device }] of positionsRef.current) {
      const dist = Math.sqrt((mx - x) ** 2 + (my - y) ** 2);
      if (dist <= 24) {
        setSelectedDevice(device);
        draggingNodeRef.current = id;
        return;
      }
    }
    // Clicked empty space
    setSelectedDevice(null);
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggingNodeRef.current === null) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = Math.max(30, Math.min(canvas.width - 30, e.clientX - rect.left));
    const my = Math.max(30, Math.min(canvas.height - 30, e.clientY - rect.top));

    const node = positionsRef.current.get(draggingNodeRef.current);
    if (node) {
      node.x = mx;
      node.y = my;
    }
  };

  const handleCanvasMouseUp = () => {
    draggingNodeRef.current = null;
  };

  if (loading) return <LoadingSpinner message="Calculating network graph topology..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  const devices = data?.devices || [];
  const zones = Array.from(new Set(devices.map(d => d.zone).filter(Boolean))) as string[];

  const currentConfigData = (selectedDevice?.config || {}) as Record<string, unknown>;
  const acls = (currentConfigData.acls as Array<{ name: string; rules: unknown[] }>) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Network className="w-7 h-7 text-cyan-400" />
            Interactive Network Topology
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Visual mesh graph with real-time zone segmentation, traffic flow animation, and node diagnostics
          </p>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAnimatingTraffic(!animatingTraffic)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
              animatingTraffic 
                ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40' 
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
          >
            {animatingTraffic ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {animatingTraffic ? 'Pause Flow' : 'Animate Traffic'}
          </button>

          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset Layout
          </button>
        </div>
      </div>

      {/* Filter & Legend Bar */}
      <div className="card p-3.5 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs text-slate-400 mr-1">Zone:</span>
          {['all', ...zones].map(z => (
            <button
              key={z}
              onClick={() => setZoneFilter(z)}
              className={`px-2.5 py-1 text-xs rounded-lg font-mono uppercase transition-colors ${
                zoneFilter === z
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 font-bold'
                  : 'text-slate-400 hover:text-white bg-slate-800/50'
              }`}
            >
              {z}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search node or IP..."
            className="w-full pl-8 pr-3 py-1 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* Topology Canvas + Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Canvas Area */}
        <div className="lg:col-span-3 card p-4 bg-slate-950 flex flex-col items-center justify-center relative overflow-hidden min-h-[580px]">
          <canvas
            ref={canvasRef}
            width={860}
            height={560}
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            className="cursor-crosshair w-full max-w-full rounded-xl bg-slate-900/40 border border-slate-800/80"
          />

          {/* Canvas Overlay Legend */}
          <div className="absolute bottom-6 left-6 p-2.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex items-center gap-4 text-[11px] font-mono text-slate-400 backdrop-blur-md">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              <span>Router</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span>Firewall</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
              <span>Switch</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span>Server</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span>Host</span>
            </div>
          </div>
        </div>

        {/* Selected Device Drawer */}
        <div className="lg:col-span-1 space-y-4">
          <div className="card p-5 space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              Node Inspector
            </h2>

            {selectedDevice ? (
              <div className="space-y-4">
                <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-base font-bold text-white font-mono">{selectedDevice.name}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-cyan-400 border border-slate-700 font-bold">
                      {selectedDevice.device_type}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 font-mono">{selectedDevice.ip_address}</div>
                </div>

                <div className="text-xs space-y-2 font-mono text-slate-300">
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">Security Zone:</span>
                    <span className="text-emerald-400 font-bold">{selectedDevice.zone || 'Global'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">Subnet CIDR:</span>
                    <span>{selectedDevice.subnet || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">VLAN ID:</span>
                    <span>{selectedDevice.vlan_id ?? 'Untagged'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">Active ACLs:</span>
                    <span className="text-cyan-400 font-semibold">{acls.length} list(s)</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-slate-500">Link Status:</span>
                    <span className="text-emerald-400 font-bold uppercase">{selectedDevice.status}</span>
                  </div>
                </div>

                <div className="pt-2">
                  <Link
                    to="/configurations"
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow-sm shadow-cyan-600/20 transition-all"
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    Inspect Full Device Config
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500 text-xs space-y-2">
                <Network className="w-8 h-8 mx-auto text-slate-600 animate-pulse" />
                <p>Click any node or link on the graph to inspect device interfaces, security zones, and ACL rules.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
