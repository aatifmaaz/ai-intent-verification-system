import { useEffect, useRef, useState, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import { getTopology } from '../api/topology';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Device } from '../types';

export const Topology = () => {
  const { data, loading, error, refetch } = useApi(getTopology);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);

  const devicePositions = useRef<Map<string, {x: number, y: number, device: Device}>>(new Map());

  useEffect(() => {
    if (!data || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const positions = new Map<string, {x: number, y: number, device: Device}>();
    const cols = Math.ceil(Math.sqrt(data.devices.length));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Calculate positions
      data.devices.forEach((dev: Device, i: number) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const x = 80 + col * 140;
        const y = 80 + row * 120;
        positions.set(String(dev.id), { x, y, device: dev });
      });

      // Draw links
      if (data.links) {
        data.links.forEach((link: { source_device_id: number; target_device_id: number; status: string }) => {
          const src = positions.get(String(link.source_device_id));
          const tgt = positions.get(String(link.target_device_id));
          if (src && tgt) {
            ctx.beginPath();
            ctx.moveTo(src.x, src.y);
            ctx.lineTo(tgt.x, tgt.y);
            ctx.strokeStyle = link.status === 'down' ? '#ef4444' : '#475569';
            ctx.lineWidth = 2;
            ctx.stroke();
          }
        });
      }

      // Draw devices
      positions.forEach(({ x, y, device }) => {
        ctx.beginPath();
        ctx.arc(x, y, 22, 0, 2 * Math.PI);
        const colors: Record<string, string> = {
          router: '#3b82f6', switch: '#8b5cf6', firewall: '#ef4444',
          server: '#10b981', client: '#f59e0b',
        };
        ctx.fillStyle = device.status === 'offline' ? '#64748b' : (colors[device.device_type] || '#6b7280');
        ctx.fill();
        ctx.strokeStyle = selectedDevice?.id === device.id ? '#22d3ee' : '#1e293b';
        ctx.lineWidth = selectedDevice?.id === device.id ? 3 : 1;
        ctx.stroke();

        ctx.fillStyle = '#e2e8f0';
        ctx.font = '11px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(device.name, x, y + 36);
      });

      devicePositions.current = positions;
    };

    draw();
  }, [data, selectedDevice]);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    for (const [, { x, y, device }] of devicePositions.current) {
      const dist = Math.sqrt((mx - x) ** 2 + (my - y) ** 2);
      if (dist <= 22) {
        setSelectedDevice(device);
        return;
      }
    }
    setSelectedDevice(null);
  }, []);

  if (loading) return <LoadingSpinner message="Loading topology..." />;
  if (error) return <ErrorMessage message={error.message} onRetry={refetch} />;

  return (
    <div className="h-full flex flex-col space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Network Topology</h1>
      </div>
      
      <div className="flex-1 flex space-x-4 min-h-[500px]">
        <div className="flex-1 card p-4 relative overflow-hidden bg-slate-900 flex items-center justify-center">
           {!data || data.devices.length === 0 ? (
             <div className="text-slate-500">No topology data available</div>
           ) : (
             <canvas 
               ref={canvasRef} 
               width={800} 
               height={600} 
               className="cursor-pointer border border-slate-800 rounded-lg"
               onClick={handleCanvasClick}
             />
           )}
        </div>
        
        <div className="w-80 card p-4 flex flex-col">
          <h2 className="text-lg font-semibold mb-4">Device Details</h2>
          {selectedDevice ? (
            <div className="space-y-3">
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider">Name</div>
                <div className="font-mono text-white">{selectedDevice.name}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider">Type</div>
                <div className="text-cyan-400 capitalize">{selectedDevice.device_type}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider">IP Address</div>
                <div className="font-mono text-white">{selectedDevice.ip_address}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider">Subnet</div>
                <div className="font-mono text-white">{selectedDevice.subnet}</div>
              </div>
              {selectedDevice.zone && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider">Zone</div>
                  <div className="text-emerald-400">{selectedDevice.zone}</div>
                </div>
              )}
              {selectedDevice.vlan_id && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider">VLAN</div>
                  <div className="font-mono text-white">{selectedDevice.vlan_id}</div>
                </div>
              )}
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider">Status</div>
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                  selectedDevice.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {selectedDevice.status}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500 text-center mt-10">
              Click a device on the graph to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
