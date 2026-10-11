import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="h-16 bg-slate-850 border-b border-slate-800 flex items-center justify-between px-6">
      <div className="text-lg font-semibold">AI-Driven Network Intent Verification</div>
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 glow-emerald"></div>
          <span className="text-sm text-slate-400">System Online</span>
        </div>
      </div>
    </header>
  );
};
