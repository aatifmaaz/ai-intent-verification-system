import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, Network, FileCode, ShieldCheck, Wrench, FlaskConical, ClipboardList, Settings } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/intents', label: 'Intent Management', icon: MessageSquare },
  { path: '/topology', label: 'Topology', icon: Network },
  { path: '/configurations', label: 'Configurations', icon: FileCode, disabled: true },
  { path: '/verification', label: 'Verification Center', icon: ShieldCheck },
  { path: '/repairs', label: 'Repairs', icon: Wrench, disabled: true },
  { path: '/simulation', label: 'Simulation', icon: FlaskConical, disabled: true },
  { path: '/audit', label: 'Audit', icon: ClipboardList, disabled: true },
  { path: '/settings', label: 'Settings', icon: Settings, disabled: true },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-850 border-r border-slate-800 flex flex-col h-full">
      <div className="p-4 border-b border-slate-800">
        <h1 className="text-xl font-bold text-cyan-500 tracking-wider">NIV PLATFORM</h1>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          item.disabled ? (
            <div key={item.label} className="flex items-center px-4 py-2 text-slate-500 cursor-not-allowed">
              <item.icon className="w-5 h-5 mr-3" />
              <span>{item.label}</span>
            </div>
          ) : (
            <NavLink
              key={item.label}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center px-4 py-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 glow-cyan'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              <span>{item.label}</span>
            </NavLink>
          )
        ))}
      </nav>
    </aside>
  );
};
