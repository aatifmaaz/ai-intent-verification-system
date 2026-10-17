import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Network, 
  FileCode, 
  ShieldCheck, 
  Wrench, 
  FlaskConical, 
  ClipboardList, 
  Settings
} from 'lucide-react';


const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/intents', label: 'Intent Management', icon: MessageSquare },
  { path: '/topology', label: 'Topology Map', icon: Network },
  { path: '/configurations', label: 'Configurations', icon: FileCode },
  { path: '/verification', label: 'Verification Center', icon: ShieldCheck },
  { path: '/repairs', label: 'Automated Repairs', icon: Wrench },
  { path: '/simulation', label: 'Simulation Lab', icon: FlaskConical },
  { path: '/audit', label: 'Audit Trail', icon: ClipboardList },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-850 border-r border-slate-800 flex flex-col h-full select-none">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold font-mono text-sm shadow-sm shadow-cyan-500/20">
            NI
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-wider flex items-center gap-1.5">
              NIV <span className="text-cyan-400 text-xs font-mono font-normal">PLATFORM</span>
            </h1>
            <p className="text-[10px] text-slate-500 font-mono">Autonomous Verification</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider px-3 py-1.5">
          Main Modules
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white border border-transparent'
              }`
            }
          >
            <div className="flex items-center">
              <item.icon className="w-4 h-4 mr-3 flex-shrink-0" />
              <span>{item.label}</span>
            </div>
          </NavLink>
        ))}
      </nav>

      {/* Footer System Indicator */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Core Online
          </span>
          <span className="text-slate-500">v2.4.0</span>
        </div>
      </div>
    </aside>
  );
};

