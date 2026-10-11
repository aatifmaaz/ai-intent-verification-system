import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  trendUp?: boolean;
  color?: 'cyan' | 'emerald' | 'amber' | 'red';
}

export const MetricCard: React.FC<MetricCardProps> = ({ title, value, icon: Icon, trend, trendUp, color = 'cyan' }) => {
  const colorStyles = {
    cyan: 'text-cyan-500',
    emerald: 'text-emerald-500',
    amber: 'text-amber-500',
    red: 'text-red-500',
  };

  return (
    <div className="card p-6 flex items-start justify-between">
      <div>
        <h3 className="text-sm font-medium text-slate-400 mb-1">{title}</h3>
        <div className="text-3xl font-bold text-white">{value}</div>
        {trend && (
          <div className={`text-sm mt-2 flex items-center ${trendUp ? 'text-emerald-400' : 'text-red-400'}`}>
            {trendUp ? '↑' : '↓'} {trend}
          </div>
        )}
      </div>
      <div className={`p-3 rounded-lg bg-slate-700/50 ${colorStyles[color]}`}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
  );
};
