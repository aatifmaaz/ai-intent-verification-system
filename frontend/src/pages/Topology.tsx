import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import { getTopology, getTopologySuggestions, TopologySuggestions } from '../api/topology';
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
  Sparkles,
  Zap
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { TopologyManagerModal } from '../components/TopologyManagerModal';
import { AutoPilotModal } from '../components/AutoPilotModal';

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
type TopologyTab = 'graph' | 'commands';

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
  const [suggestionsData, setSuggestionsData] = useState<TopologySuggestions | null>(null);
  const [isAutoPilotOpen, setIsAutoPilotOpen] = useState(false);
  const [autoPilotPrompt, setAutoPilotPrompt] = useState('');
  const [activeTab, setActiveTab] = useState<TopologyTab>('graph');

  useEffect(() => {
    getTopologySuggestions()
      .then(setSuggestionsData)
      .catch(() => {});
  }, [data]);
  
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

      const tierY = [88, 222, 360, 498];
      const tierStartX = 150;
      const tierEndX = width - 82;
      [0, 1, 2, 3].forEach((tierIndex) => {
        const devs = tierMap[tierIndex];
        const count = devs.length;
        if (count === 0) return;
        const step = count > 1 ? (tierEndX - tierStartX) / (count - 1) : 0;

        devs.forEach((dev, idx) => {
          const x = count === 1 ? (tierStartX + tierEndX) / 2 : tierStartX + idx * step;
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
      const clusterRadius = Math.min(width, height) * 0.34;

      zoneKeys.forEach((zk, zIdx) => {
        const zoneAngle = (2 * Math.PI * zIdx) / (zoneCount || 1) - Math.PI / 2;
        const groupCenterX = centerX + Math.cos(zoneAngle) * clusterRadius;
        const groupCenterY = centerY + Math.sin(zoneAngle) * clusterRadius;

        const devs = zoneGroups[zk];
        devs.forEach((dev, dIdx) => {
          const subAngle = (2 * Math.PI * dIdx) / (devs.length || 1);
        const subDist = devs.length > 1 ? 76 : 0;
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
      const activeRequirement = data?.active_requirements?.[0];
      const activePolicy = activeRequirement?.policies?.[0];
      const endpointMatches = (device: Device, zone: string | null | undefined, network: string | null | undefined) => {
        if (network) {
          const host = network.split('/')[0];
          if (device.ip_address === host || device.subnet === network) return true;
          if (network.includes('/') && device.subnet === network) return true;
          return false;
        }
        return Boolean(zone && device.zone?.toLowerCase() === zone.toLowerCase());
      };
      const sourceDevices = activePolicy
        ? (data?.devices || []).filter((device) => endpointMatches(device, activePolicy.source_zone, activePolicy.source_network))
        : [];
      const destinationDevices = activePolicy
        ? (data?.devices || []).filter((device) => endpointMatches(device, activePolicy.destination_zone, activePolicy.destination_network))
        : [];
      const destinationIds = new Set(destinationDevices.map((device) => device.id));
      const policyPathLinkIds = new Set<number>();
      for (const source of sourceDevices) {
        const queue = [source.id];
        const previous = new Map<number, { node: number; link: NetworkLink }>();
        const visited = new Set(queue);
        let found: number | null = null;
        while (queue.length && found === null) {
          const current = queue.shift()!;
          if (destinationIds.has(current)) { found = current; break; }
          for (const link of links) {
            const next = link.source_device_id === current ? link.target_device_id
              : link.target_device_id === current ? link.source_device_id : null;
            if (next === null || visited.has(next)) continue;
            visited.add(next);
            previous.set(next, { node: current, link });
            queue.push(next);
          }
        }
        if (found === null || found === source.id) continue;
        let cursor = found;
        while (previous.has(cursor)) {
          const step = previous.get(cursor)!;
          policyPathLinkIds.add(step.link.id);
          cursor = step.node;
        }
        if (policyPathLinkIds.size) break;
      }

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

      if (layoutMode === 'tiered') {
        const lanes = [
          { y: 88, label: 'PERIMETER' },
          { y: 222, label: 'CORE & DISTRIBUTION' },
          { y: 360, label: 'SERVICES' },
          { y: 498, label: 'ENDPOINTS' },
        ];
        lanes.forEach(({ y, label }, index) => {
          ctx.beginPath();
          ctx.roundRect(18, y - 36, width - 36, 72, 13);
          ctx.fillStyle = index % 2 === 0 ? 'rgba(15, 23, 42, 0.44)' : 'rgba(30, 41, 59, 0.24)';
          ctx.fill();
          ctx.strokeStyle = 'rgba(71, 85, 105, 0.22)';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.fillStyle = '#64748b';
          ctx.font = 'bold 9px sans-serif';
          ctx.textAlign = 'left';
          ctx.fillText(label, 28, y - 25);
        });
      }

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
        const isPolicyPath = policyPathLinkIds.has(link.id);
        const isDeniedPolicyPath = isPolicyPath && (
          activePolicy?.action === 'deny' || activePolicy?.policy_type === 'deny' || activePolicy?.policy_type === 'isolate'
        );

        // A denied policy breaks the visual traffic path with an X marker; the
        // underlying device-to-device topology link remains physically present.
        if (isDeniedPolicyPath) {
          const dx = tgt.x - src.x;
          const dy = tgt.y - src.y;
          ctx.strokeStyle = '#fb7185';
          ctx.lineWidth = 4;
          ctx.setLineDash([8, 5]);
          ctx.shadowColor = '#fb7185';
          ctx.shadowBlur = 9;
          for (const [start, end] of [[0, 0.38], [0.62, 1]]) {
            ctx.beginPath();
            ctx.moveTo(src.x + dx * start, src.y + dy * start);
            ctx.lineTo(src.x + dx * end, src.y + dy * end);
            ctx.stroke();
          }
          ctx.setLineDash([]);
          ctx.shadowBlur = 0;

          const midX = src.x + dx * 0.5;
          const midY = src.y + dy * 0.5;
          ctx.beginPath();
          ctx.arc(midX, midY, 9, 0, 2 * Math.PI);
          ctx.fillStyle = '#450a0a';
          ctx.fill();
          ctx.strokeStyle = '#fb7185';
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(midX - 3.5, midY - 3.5);
          ctx.lineTo(midX + 3.5, midY + 3.5);
          ctx.moveTo(midX + 3.5, midY - 3.5);
          ctx.lineTo(midX - 3.5, midY + 3.5);
          ctx.strokeStyle = '#fff1f2';
          ctx.lineWidth = 2;
          ctx.stroke();
        } else {
          // Draw normal or allowed policy path.
          ctx.beginPath();
          ctx.moveTo(src.x, src.y);
          ctx.lineTo(tgt.x, tgt.y);

          if (isPolicyPath) {
            ctx.strokeStyle = '#34d399';
            ctx.lineWidth = 4;
            ctx.setLineDash([9, 6]);
            ctx.shadowColor = ctx.strokeStyle;
            ctx.shadowBlur = 9;
          } else if (isHighlighted) {
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
          ctx.setLineDash([]);
          ctx.shadowBlur = 0; // reset
        }

        // Animate packets flowing along active link
        if (animatingTraffic && link.status !== 'down' && !isDimmed && !isDeniedPolicyPath) {
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

      // Draw Device Cards
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

        const cardWidth = 150;
        const cardHeight = 62;
        const left = x - cardWidth / 2;
        const top = y - cardHeight / 2;

        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.roundRect(left - 3, top - 3, cardWidth + 6, cardHeight + 6, 13);
          ctx.fillStyle = isSelected ? 'rgba(34, 211, 238, 0.13)' : 'rgba(56, 189, 248, 0.08)';
          ctx.fill();
          ctx.strokeStyle = isSelected ? '#22d3ee' : '#38bdf8';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        ctx.beginPath();
        ctx.roundRect(left, top, cardWidth, cardHeight, 10);
        ctx.fillStyle = isDimmed ? 'rgba(15, 23, 42, 0.94)' : 'rgba(15, 23, 42, 0.98)';
        ctx.fill();
        ctx.strokeStyle = isSelected ? '#22d3ee' : isDimmed ? '#334155' : colors.border;
        ctx.lineWidth = isSelected ? 2 : 1.2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(left + 19, y, 10, 0, 2 * Math.PI);
        ctx.fillStyle = isDimmed ? '#334155' : colors.bg;
        ctx.fill();
        ctx.strokeStyle = isDimmed ? '#475569' : colors.border;
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(left + cardWidth - 11, top + 11, 3.5, 0, 2 * Math.PI);
        ctx.fillStyle = device.status === 'active' ? '#34d399' : '#fb7185';
        ctx.fill();

        const displayName = device.name.length > 18 ? `${device.name.slice(0, 17)}…` : device.name;
        ctx.textAlign = 'left';
        ctx.font = isSelected || isHovered ? 'bold 12px monospace' : '12px monospace';
        ctx.fillStyle = isDimmed ? '#64748b' : '#f8fafc';
        ctx.fillText(displayName, left + 34, y - 2, 105);
        ctx.font = '10px sans-serif';
        ctx.fillStyle = isDimmed ? '#475569' : '#94a3b8';
        ctx.fillText(`${device.device_type.toUpperCase()}  ·  ${device.zone || device.ip_address}`, left + 34, y + 16, 105);
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
      if (Math.abs(mx - x) <= 72 && Math.abs(my - y) <= 32) {
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
            if (Math.abs(mx - x) <= 72 && Math.abs(my - y) <= 32) {
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

  // Keep the existing topology and Auto-Pilot modal mounted while refreshing
  // after an enforcement run. Replacing the whole page here hides its result.
  if (loading && !data) return <LoadingSpinner message="Calculating network graph topology..." />;
  if (error && !data) return <ErrorMessage message={error.message} onRetry={refetch} />;

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

      <div className="flex items-center gap-1 border-b border-slate-800" role="tablist" aria-label="Topology views">
        <button type="button" role="tab" aria-selected={activeTab === 'graph'} onClick={() => setActiveTab('graph')} className={`px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${activeTab === 'graph' ? 'border-cyan-400 text-cyan-300' : 'border-transparent text-slate-400 hover:text-white'}`}>
          Network Graph
        </button>
        <button type="button" role="tab" aria-selected={activeTab === 'commands'} onClick={() => setActiveTab('commands')} className={`px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${activeTab === 'commands' ? 'border-cyan-400 text-cyan-300' : 'border-transparent text-slate-400 hover:text-white'}`}>
          Command Guide
        </button>
      </div>

      {activeTab === 'commands' ? (
        <section className="card p-5 space-y-5" role="tabpanel" aria-label="Supported topology commands">
          <div>
            <h2 className="text-base font-bold text-white">Natural-language enforcement commands</h2>
            <p className="mt-1 text-sm text-slate-400">Enter these in Auto-Enforce. Use your actual device names, network names, or zones.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {[
              { title: 'Block or deny traffic', examples: ['Block guest network from accessing the database server.', 'Stop edge-router from reaching core-router.', 'The guest network must not communicate with the HR network.'] },
              { title: 'Allow or require access', examples: ['Allow engineering network to access the application server.', 'All devices in the engineering network must be able to access the internal application server.', 'The app server must be reachable by engineering.'] },
              { title: 'Limit a service', examples: ['Allow engineering network to access the app server on port 443.', 'Block guest network from reaching the database over port 5432.', 'Allow SSH from management to core-router.'] },
              { title: 'Scope by device or subnet', examples: ['Deny 10.0.1.0/24 from 10.0.0.0/24.', 'Stop edge-router from core-router.', 'Isolate the guest network from the HR network.'] },
            ].map((group) => (
              <div key={group.title} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <h3 className="text-sm font-semibold text-cyan-300">{group.title}</h3>
                <ul className="mt-2 space-y-2">
                  {group.examples.map((example) => <li key={example} className="rounded-lg bg-slate-950/70 px-3 py-2 font-mono text-xs text-slate-200">“{example}”</li>)}
                </ul>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-100">
            <strong className="text-amber-300">Physical links:</strong> To create one, open Auto-Pilot and enter “Connect edge-router to main-firewall directly” or “Create a link between edge-router and main-firewall.” The node names must match the topology. “Disconnect” and “stop X from Y” create a deny policy; they do not remove a physical graph link. Select <strong>Network Graph</strong> to inspect the topology.
          </div>
        </section>
      ) : <>

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

      {/* Recommended Enforcements Banner for Active Blueprint */}
      {suggestionsData && suggestionsData.suggestions && suggestionsData.suggestions.length > 0 && (
        <div className="card p-3 bg-gradient-to-r from-slate-900 via-cyan-950/25 to-slate-900 border border-cyan-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-lg shadow-cyan-950/20 animate-fadeIn">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
              <Zap className="w-3.5 h-3.5 fill-cyan-400" />
            </div>
            <div>
              <span className="text-xs font-bold text-white tracking-wide flex items-center gap-1.5">
                Recommended Enforcements for <span className="text-cyan-300 font-bold">{suggestionsData.template_name}:</span>
              </span>
              <span className="text-[10px] text-slate-400 font-mono block">
                Click any real-world requirement to test instant autonomous enforcement
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
            {suggestionsData.suggestions.slice(0, 3).map((sugg, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setAutoPilotPrompt(sugg);
                  setIsAutoPilotOpen(true);
                }}
                className="px-2.5 py-1 text-xs rounded-lg bg-cyan-950/40 hover:bg-cyan-900/60 text-cyan-300 hover:text-white border border-cyan-500/30 hover:border-cyan-400 transition-all font-mono text-left flex items-center gap-1.5 hover:scale-[1.02] active:scale-[0.98]"
                title="Click to run Auto-Pilot enforcement on this network"
              >
                <Sparkles className="w-3 h-3 text-cyan-400 flex-shrink-0" />
                <span className="truncate max-w-[280px]">"{sugg}"</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Topology Canvas + Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Canvas Area */}
        <div className="lg:col-span-3 card p-4 bg-slate-950 flex flex-col items-center justify-center relative overflow-hidden min-h-[580px]">
          {data?.active_requirements?.[0] && (
            <div className="absolute top-6 left-6 z-10 max-w-[62%] rounded-lg border border-rose-500/40 bg-slate-950/95 px-3 py-2 shadow-lg shadow-rose-950/30">
              <div className="text-[10px] font-bold uppercase tracking-wider text-rose-300">
                Active requirement · {data.active_requirements[0].policies[0]?.action || data.active_requirements[0].policies[0]?.policy_type}
              </div>
              <div className="mt-1 truncate text-xs font-mono text-white" title={data.active_requirements[0].natural_language}>
                {data.active_requirements[0].natural_language}
              </div>
              {(data.active_requirements[0].policies[0]?.action === 'deny' || data.active_requirements[0].policies[0]?.policy_type === 'deny' || data.active_requirements[0].policies[0]?.policy_type === 'isolate') && (
                <div className="mt-1 text-[9px] text-rose-200/80">Red break + × means traffic blocked; physical link remains.</div>
              )}
            </div>
          )}
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

      </>}

      {/* Switch / Import Topology Studio Modal */}
      <TopologyManagerModal
        isOpen={isTopologyModalOpen}
        onClose={() => setIsTopologyModalOpen(false)}
        onTopologyChanged={() => {
          refetch();
          handleResetView();
          getTopologySuggestions().then(setSuggestionsData).catch(() => {});
        }}
      />

      {/* Autonomous Auto-Pilot Modal */}
      <AutoPilotModal
        isOpen={isAutoPilotOpen}
        onClose={() => setIsAutoPilotOpen(false)}
        defaultPrompt={autoPilotPrompt}
        onSuccess={() => {
          refetch();
          getTopologySuggestions().then(setSuggestionsData).catch(() => {});
        }}
      />
    </div>
  );
};
