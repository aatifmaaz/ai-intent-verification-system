import React, { useEffect, useRef, useState, useCallback } from 'react';
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
  ExternalLink,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Layers,
  Activity,
  Shield,
  Radio,
  Sparkles
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { TopologyManagerModal } from '../components/TopologyManagerModal';

interface NodePos {
  id: number;
  x: number;
  y: number;
  device: Device;
}

const TYPE_CONFIG: Record<string, { bg: string; border: string; glow: string; label: string }> = {
  router: { bg: '#1d4ed8', border: '#60a5fa', glow: 'rgba(59, 130, 246, 0.5)', label: 'Router' },
  switch: { bg: '#6d28d9', border: '#a78bfa', glow: 'rgba(139, 92, 246, 0.5)', label: 'Switch' },
  firewall: { bg: '#b91c1c', border: '#f87171', glow: 'rgba(239, 68, 68, 0.5)', label: 'Firewall' },
  server: { bg: '#047857', border: '#34d399', glow: 'rgba(16, 185, 129, 0.5)', label: 'Server' },
  host: { bg: '#b45309', border: '#fbbf24', glow: 'rgba(245, 158, 11, 0.5)', label: 'Host' },
  client: { bg: '#b45309', border: '#fbbf24', glow: 'rgba(245, 158, 11, 0.5)', label: 'Client' },
};

type LayoutMode = 'tiered' | 'zones' | 'radial';

export const Topology: React.FC = () => {
  const { data, loading, error, refetch } = useApi(getTopology);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [selectedLink, setSelectedLink] = useState<NetworkLink | null>(null);
  const [hoveredNode, setHoveredNode] = useState<Device | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [animatingTraffic, setAnimatingTraffic] = useState(true);
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('tiered');
  const [isTopologyModalOpen, setIsTopologyModalOpen] = useState(false);
  
  // Transform: Pan and Zoom
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState<number>(1);


  const positionsRef = useRef<Map<number, NodePos>>(new Map());
  const animationFrameRef = useRef<number | null>(null);
  const pulseOffsetRef = useRef<number>(0);
  
  // Dragging state
  const isDraggingNodeRef = useRef<number | null>(null);
  const isPanningCanvasRef = useRef<boolean>(false);
  const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Calculate layout coordinates
  const computeInitialLayout = useCallback((devices: Device[], mode: LayoutMode, width: number, height: number) => {
    const newPositions = new Map<number, NodePos>();
    if (!devices || devices.length === 0) return newPositions;

    const centerX = width / 2;
    const centerY = height / 2;

    if (mode === 'tiered') {
      // 4-Tier Architectural Hierarchy (Clean Visual Layers)
      // Tier 0: External / Perimeter (edge-router, main-firewall, web-server)
      // Tier 1: Core Distribution (core-router, distribution-switch-1, distribution-switch-2)
      // Tier 2: Servers (hr-server, eng-server, app-server, db-server, backup-server)
      // Tier 3: Client Endpoints (hr-clients, eng-clients, guest-clients, mgmt-clients)

      const tierMap: Record<number, Device[]> = { 0: [], 1: [], 2: [], 3: [] };

      devices.forEach((dev) => {
        const name = dev.name.toLowerCase();
        const type = dev.device_type.toLowerCase();
        const zone = (dev.zone || '').toLowerCase();

        if (name.includes('edge') || name.includes('firewall') || zone === 'dmz') {
          tierMap[0].push(dev);
        } else if (type === 'router' || type === 'switch' || zone.includes('core') || zone.includes('dist')) {
          tierMap[1].push(dev);
        } else if (type === 'server') {
          tierMap[2].push(dev);
        } else {
          tierMap[3].push(dev);
        }
      });

      const tierY = [80, 200, 340, 480];
      [0, 1, 2, 3].forEach((tierIndex) => {
        const devs = tierMap[tierIndex];
        const count = devs.length;
        if (count === 0) return;
        const totalSpan = Math.min(width - 160, Math.max(300, count * 140));
        const startX = centerX - totalSpan / 2;
        const step = count > 1 ? totalSpan / (count - 1) : 0;

        devs.forEach((dev, idx) => {
          const x = count === 1 ? centerX : startX + idx * step;
          const y = tierY[tierIndex];
          newPositions.set(dev.id, { id: dev.id, x, y, device: dev });
        });
      });
    } else if (mode === 'zones') {
      // Clustered by Zone
      const zoneGroups: Record<string, Device[]> = {};
      devices.forEach((dev) => {
        const z = dev.zone || 'global';
        if (!zoneGroups[z]) zoneGroups[z] = [];
        zoneGroups[z].push(dev);
      });

      const zoneKeys = Object.keys(zoneGroups);
      const zoneCount = zoneKeys.length;
      const clusterRadius = Math.min(width, height) * 0.36;

      zoneKeys.forEach((zk, zIdx) => {
        const zoneAngle = (2 * Math.PI * zIdx) / (zoneCount || 1) - Math.PI / 2;
        const groupCenterX = centerX + Math.cos(zoneAngle) * clusterRadius;
        const groupCenterY = centerY + Math.sin(zoneAngle) * clusterRadius;

        const devs = zoneGroups[zk];
        devs.forEach((dev, dIdx) => {
          const subAngle = (2 * Math.PI * dIdx) / (devs.length || 1);
          const subDist = devs.length > 1 ? 40 : 0;
          const x = groupCenterX + Math.cos(subAngle) * subDist;
          const y = groupCenterY + Math.sin(subAngle) * subDist;
          newPositions.set(dev.id, { id: dev.id, x, y, device: dev });
        });
      });
    } else {
      // Radial ring
      const isCore = (d: Device) => d.name.toLowerCase().includes('core') || d.name.toLowerCase().includes('firewall');
      const coreNodes = devices.filter(isCore);
      const outerNodes = devices.filter((d) => !isCore(d));

      coreNodes.forEach((dev, i) => {
        const angle = (2 * Math.PI * i) / (coreNodes.length || 1);
        const r = 90;
        newPositions.set(dev.id, { id: dev.id, x: centerX + Math.cos(angle) * r, y: centerY + Math.sin(angle) * r, device: dev });
      });

      outerNodes.forEach((dev, i) => {
        const angle = (2 * Math.PI * i) / (outerNodes.length || 1);
        const r = 210;
        newPositions.set(dev.id, { id: dev.id, x: centerX + Math.cos(angle) * r, y: centerY + Math.sin(angle) * r, device: dev });
      });
    }

    return newPositions;
  }, []);

  // Initialize node layout whenever data or layout mode changes
  useEffect(() => {
    if (!data?.devices) return;
    const canvas = canvasRef.current;
    const width = canvas ? canvas.width : 900;
    const height = canvas ? canvas.height : 580;

    positionsRef.current = computeInitialLayout(data.devices, layoutMode, width, height);
    // Reset pan/zoom on layout mode change
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, [data, layoutMode, computeInitialLayout]);

  // Main Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let isRunning = true;

    const render = () => {
      if (!isRunning) return;

      const width = canvas.width;
      const height = canvas.height;

      // Clear Canvas
      ctx.clearRect(0, 0, width, height);

      // Save context for Pan & Zoom transforms
      ctx.save();
      ctx.translate(pan.x, pan.y);
      ctx.scale(zoom, zoom);

      const positions = positionsRef.current;
      const links = data?.links || [];

      // Advance pulse offset for packet animation
      if (animatingTraffic) {
        pulseOffsetRef.current = (pulseOffsetRef.current + 0.015) % 1;
      }

      // Draw Subtle Background Grid
      ctx.save();
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.2)';
      ctx.lineWidth = 1 / zoom;
      const gridSize = 40;
      const minX = -pan.x / zoom;
      const maxX = (width - pan.x) / zoom;
      const minY = -pan.y / zoom;
      const maxY = (height - pan.y) / zoom;

      for (let gx = Math.floor(minX / gridSize) * gridSize; gx <= maxX; gx += gridSize) {
        ctx.beginPath();
        ctx.moveTo(gx, minY);
        ctx.lineTo(gx, maxY);
        ctx.stroke();
      }
      for (let gy = Math.floor(minY / gridSize) * gridSize; gy <= maxY; gy += gridSize) {
        ctx.beginPath();
        ctx.moveTo(minX, gy);
        ctx.lineTo(maxX, gy);
        ctx.stroke();
      }
      ctx.restore();

      // Draw Links
      links.forEach((link: NetworkLink) => {
        const src = positions.get(link.source_device_id);
        const tgt = positions.get(link.target_device_id);
        if (!src || !tgt) return;

        const isLinkSelected = selectedLink && selectedLink.id === link.id;
        const isConnectedToSelected = selectedDevice && 
          (link.source_device_id === selectedDevice.id || link.target_device_id === selectedDevice.id);
        const isConnectedToHovered = hoveredNode &&
          (link.source_device_id === hoveredNode.id || link.target_device_id === hoveredNode.id);

        const srcMatches = zoneFilter === 'all' || src.device.zone === zoneFilter;
        const tgtMatches = zoneFilter === 'all' || tgt.device.zone === zoneFilter;
        const isDimmed = zoneFilter !== 'all' && !srcMatches && !tgtMatches;

        const isHighlighted = isLinkSelected || isConnectedToSelected || isConnectedToHovered;

        // Draw line
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);

        if (isHighlighted) {
          ctx.strokeStyle = '#22d3ee';
          ctx.lineWidth = 2.5;
          ctx.shadowColor = 'rgba(34, 211, 238, 0.6)';
          ctx.shadowBlur = 8;
        } else if (link.status === 'down') {
          ctx.strokeStyle = '#ef4444';
          ctx.lineWidth = 1.8;
          ctx.shadowBlur = 0;
        } else if (isDimmed) {
          ctx.strokeStyle = '#1e293b';
          ctx.lineWidth = 1;
          ctx.shadowBlur = 0;
        } else {
          ctx.strokeStyle = '#334155';
          ctx.lineWidth = 1.5;
          ctx.shadowBlur = 0;
        }
        ctx.stroke();
        ctx.shadowBlur = 0; // reset

        // Animate packets flowing along active link
        if (animatingTraffic && link.status !== 'down' && !isDimmed) {
          const t = (pulseOffsetRef.current + (link.id * 0.17)) % 1;
          const px = src.x + (tgt.x - src.x) * t;
          const py = src.y + (tgt.y - src.y) * t;

          ctx.beginPath();
          ctx.arc(px, py, isHighlighted ? 4 : 2.5, 0, 2 * Math.PI);
          ctx.fillStyle = isHighlighted ? '#38bdf8' : '#0284c7';
          ctx.shadowColor = '#38bdf8';
          ctx.shadowBlur = isHighlighted ? 8 : 4;
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      });

      // Draw Nodes
      positions.forEach(({ x, y, device }) => {
        const isSelected = selectedDevice?.id === device.id;
        const isHovered = hoveredNode?.id === device.id;
        const isMatchesZone = zoneFilter === 'all' || device.zone === zoneFilter;
        const isMatchesSearch = !searchQuery || 
          device.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          device.ip_address.includes(searchQuery) ||
          (device.zone && device.zone.toLowerCase().includes(searchQuery.toLowerCase()));

        const isDimmed = !isMatchesZone || !isMatchesSearch;
        const colors = TYPE_CONFIG[device.device_type] || TYPE_CONFIG.router;

        // Selection / Hover Aura
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(x, y, 26, 0, 2 * Math.PI);
          ctx.fillStyle = isSelected ? 'rgba(34, 211, 238, 0.25)' : 'rgba(56, 189, 248, 0.15)';
          ctx.fill();
          ctx.strokeStyle = isSelected ? '#22d3ee' : '#38bdf8';
          ctx.lineWidth = isSelected ? 2.5 : 1.5;
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

        // Status Indicator Dot
        ctx.beginPath();
        ctx.arc(x + 12, y - 12, 4.5, 0, 2 * Math.PI);
        ctx.fillStyle = device.status === 'active' ? '#10b981' : '#ef4444';
        ctx.fill();
        ctx.strokeStyle = '#0f172a';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Node Label
        ctx.font = isSelected || isHovered ? 'bold 11px monospace' : '10px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = isSelected ? '#22d3ee' : isHovered ? '#38bdf8' : isDimmed ? '#475569' : '#f1f5f9';
        ctx.fillText(device.name, x, y + 32);

        // Subnet / Zone Subtext
        if (!isDimmed) {
          ctx.font = '9px monospace';
          ctx.fillStyle = '#64748b';
          ctx.fillText(device.zone ? `[${device.zone}]` : device.ip_address, x, y + 43);
        }
      });

      ctx.restore();

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      isRunning = false;
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [data, selectedDevice, selectedLink, hoveredNode, zoneFilter, searchQuery, animatingTraffic, pan, zoom]);

  // Convert Mouse Event screen coordinates accurately to World Coordinates
  const getCanvasWorldCoords = useCallback((e: React.MouseEvent<HTMLCanvasElement> | MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const clientX = (e.clientX - rect.left) * scaleX;
    const clientY = (e.clientY - rect.top) * scaleY;

    // Transform by current Pan and Zoom
    const worldX = (clientX - pan.x) / zoom;
    const worldY = (clientY - pan.y) / zoom;
    return { x: worldX, y: worldY };
  }, [pan, zoom]);

  // Mouse Down: Node Click / Drag Start / Pan Start
  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x: mx, y: my } = getCanvasWorldCoords(e);

    // Check node hit
    for (const [id, { x, y, device }] of positionsRef.current) {
      const dist = Math.sqrt((mx - x) ** 2 + (my - y) ** 2);
      if (dist <= 22) {
        setSelectedDevice(device);
        setSelectedLink(null);
        isDraggingNodeRef.current = id;
        return;
      }
    }

    // Check link hit
    const links = data?.links || [];
    for (const link of links) {
      const src = positionsRef.current.get(link.source_device_id);
      const tgt = positionsRef.current.get(link.target_device_id);
      if (!src || !tgt) continue;

      // Distance from point to line segment
      const dx = tgt.x - src.x;
      const dy = tgt.y - src.y;
      const lenSq = dx * dx + dy * dy;
      if (lenSq === 0) continue;
      const t = Math.max(0, Math.min(1, ((mx - src.x) * dx + (my - src.y) * dy) / lenSq));
      const projX = src.x + t * dx;
      const projY = src.y + t * dy;
      const dist = Math.sqrt((mx - projX) ** 2 + (my - projY) ** 2);
      if (dist <= 7) {
        setSelectedLink(link);
        return;
      }
    }

    // Clicked empty background: deselect & start panning
    setSelectedDevice(null);
    setSelectedLink(null);
    isPanningCanvasRef.current = true;
    panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  // Window-level Mouse Move for fluid, un-stuck dragging & panning
  useEffect(() => {
    const handleWindowMouseMove = (e: MouseEvent) => {
      if (isDraggingNodeRef.current !== null) {
        const { x: mx, y: my } = getCanvasWorldCoords(e);
        const node = positionsRef.current.get(isDraggingNodeRef.current);
        if (node) {
          node.x = mx;
          node.y = my;
        }
      } else if (isPanningCanvasRef.current) {
        setPan({
          x: e.clientX - panStartRef.current.x,
          y: e.clientY - panStartRef.current.y
        });
      } else {
        // Hover detection
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        if (
          e.clientX >= rect.left &&
          e.clientX <= rect.right &&
          e.clientY >= rect.top &&
          e.clientY <= rect.bottom
        ) {
          const { x: mx, y: my } = getCanvasWorldCoords(e);
          let foundHover: Device | null = null;
          for (const [, { x, y, device }] of positionsRef.current) {
            const dist = Math.sqrt((mx - x) ** 2 + (my - y) ** 2);
            if (dist <= 22) {
              foundHover = device;
              break;
            }
          }
          setHoveredNode(foundHover);
        } else {
          setHoveredNode(null);
        }
      }
    };

    const handleWindowMouseUp = () => {
      isDraggingNodeRef.current = null;
      isPanningCanvasRef.current = false;
    };

    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleWindowMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleWindowMouseMove);
      window.removeEventListener('mouseup', handleWindowMouseUp);
    };
  }, [getCanvasWorldCoords]);

  // Mouse Wheel Zoom
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prevZoom) => {
      const nextZoom = Math.max(0.4, Math.min(2.5, prevZoom * zoomFactor));
      return Number(nextZoom.toFixed(2));
    });
  };

  // Zoom control buttons
  const handleZoomIn = () => setZoom((z) => Math.min(2.5, Number((z + 0.15).toFixed(2))));
  const handleZoomOut = () => setZoom((z) => Math.max(0.4, Number((z - 0.15).toFixed(2))));
  const handleResetView = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
    if (data?.devices && canvasRef.current) {
      positionsRef.current = computeInitialLayout(data.devices, layoutMode, canvasRef.current.width, canvasRef.current.height);
    }
  };

  if (loading) return <LoadingSpinner message="Calculating network graph topology..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  const devices = data?.devices || [];
  const links = data?.links || [];
  const zones = Array.from(new Set(devices.map(d => d.zone).filter(Boolean))) as string[];

  const currentConfigData = (selectedDevice?.config || {}) as Record<string, unknown>;
  const acls = (currentConfigData.acls as Array<{ name: string; rules: unknown[] }>) || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Network className="w-7 h-7 text-cyan-400" />
            Interactive Network Topology
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic zero-trust network graph. Drag nodes to reposition, pan and zoom, or click any device to inspect real ACL policies.
          </p>
        </div>

        {/* Toolbar & Layout Switcher */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Layout Mode Selector */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <button
              onClick={() => setLayoutMode('tiered')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors ${
                layoutMode === 'tiered' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
              title="Hierarchical 4-Tier Architecture"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Tiered</span>
            </button>
            <button
              onClick={() => setLayoutMode('zones')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors ${
                layoutMode === 'zones' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
              title="Grouped by Security Zones"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Zones</span>
            </button>
            <button
              onClick={() => setLayoutMode('radial')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors ${
                layoutMode === 'radial' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
              title="Radial Mesh Ring"
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Radial</span>
            </button>
          </div>

          <button
            onClick={() => setAnimatingTraffic(!animatingTraffic)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
              animatingTraffic 
                ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40' 
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
          >
            {animatingTraffic ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {animatingTraffic ? 'Pause Traffic' : 'Animate Traffic'}
          </button>

          <button
            onClick={handleResetView}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 transition-colors"
            title="Reset positions and zoom to default"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset Layout
          </button>

          <button
            onClick={() => setIsTopologyModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-md shadow-cyan-600/30 transition-all border border-cyan-400/30 hover:scale-[1.02] active:scale-[0.98]"
            title="Switch templates or import a completely new custom network topology"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-200" />
            <span>Switch / Import Topology</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
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
            placeholder="Search node, IP, or zone..."
            className="w-full pl-8 pr-3 py-1 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
          />
        </div>
      </div>

      {/* Topology Canvas + Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Canvas Area */}
        <div className="lg:col-span-3 card p-4 bg-slate-950 flex flex-col items-center justify-center relative overflow-hidden min-h-[580px]">
          <canvas
            ref={canvasRef}
            width={900}
            height={580}
            onMouseDown={handleCanvasMouseDown}
            onWheel={handleWheel}
            className="cursor-grab active:cursor-grabbing w-full h-[580px] rounded-xl bg-slate-900/40 border border-slate-800/80 block"
          />

          {/* Floating Canvas Controls (Zoom In/Out, Reset, Fit) */}
          <div className="absolute top-6 right-6 flex items-center gap-1.5 p-1.5 rounded-lg bg-slate-900/90 border border-slate-800/80 shadow-lg backdrop-blur-md text-slate-300">
            <button
              onClick={handleZoomIn}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-cyan-400 transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-cyan-400 transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleResetView}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-cyan-400 transition-colors"
              title="Reset View"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <span className="text-[11px] font-mono px-2 py-0.5 text-slate-400 border-l border-slate-800">
              {Math.round(zoom * 100)}%
            </span>
          </div>

          {/* Canvas Overlay Legend */}
          <div className="absolute bottom-6 left-6 p-2.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex flex-wrap items-center gap-4 text-[11px] font-mono text-slate-400 backdrop-blur-md">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm" />
              <span>Router</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-sm" />
              <span>Firewall</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-sm" />
              <span>Switch</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm" />
              <span>Server</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-sm" />
              <span>Endpoint</span>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 pl-2 border-l border-slate-800 text-slate-500 text-[10px]">
              <span>Drag nodes &middot; Scroll to zoom</span>
            </div>
          </div>
        </div>

        {/* Selected Device / Link Drawer */}
        <div className="lg:col-span-1 space-y-4">
          <div className="card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Server className="w-4 h-4 text-cyan-400" />
                Graph Inspector
              </h2>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                {devices.length} Nodes Online
              </span>
            </div>

            {selectedDevice ? (
              <div className="space-y-4 animate-fadeIn">
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
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">Link Status:</span>
                    <span className="text-emerald-400 font-bold uppercase">{selectedDevice.status}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-slate-500">Direct Links:</span>
                    <span className="text-slate-200">
                      {links.filter(l => l.source_device_id === selectedDevice.id || l.target_device_id === selectedDevice.id).length} links
                    </span>
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
            ) : selectedLink ? (
              <div className="space-y-4 animate-fadeIn">
                <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-white font-mono flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5 text-cyan-400" />
                      Link #{selectedLink.id}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">
                      {selectedLink.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 font-mono">
                    {devices.find(d => d.id === selectedLink.source_device_id)?.name} &harr; {devices.find(d => d.id === selectedLink.target_device_id)?.name}
                  </div>
                </div>

                <div className="text-xs space-y-2 font-mono text-slate-300">
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">Bandwidth:</span>
                    <span className="text-cyan-400 font-bold">{selectedLink.bandwidth || '1 Gbps Full-Duplex'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">Latency:</span>
                    <span className="text-emerald-400 font-bold">&lt; 0.5 ms</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-500">Packet Flow:</span>
                    <span className="text-emerald-400">Bidirectional</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500 text-xs space-y-3">
                <Network className="w-8 h-8 mx-auto text-slate-600 animate-pulse" />
                <p>Click any node or link on the canvas to inspect device interfaces, security zones, and ACL rules.</p>
                <div className="text-[11px] text-cyan-400 font-mono">
                  Tip: Use the 'Tiered' or 'Zones' layout buttons above to organize the mesh.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Switch / Import Topology Studio Modal */}
      <TopologyManagerModal
        isOpen={isTopologyModalOpen}
        onClose={() => setIsTopologyModalOpen(false)}
        onTopologyChanged={() => {
          refetch();
          handleResetView();
        }}
      />
    </div>
  );
};
