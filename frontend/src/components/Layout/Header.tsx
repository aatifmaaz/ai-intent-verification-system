import React, { useState } from 'react';
import { Play, CheckCircle, RefreshCw } from 'lucide-react';
import { runVerification } from '../../api/verification';


export const Header: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [quickNotice, setQuickNotice] = useState<string | null>(null);

  const handleQuickVerification = async () => {
    setIsRunning(true);
    setQuickNotice(null);
    try {
      const res = await runVerification();
      setQuickNotice(`Verification run completed: ${res.passed} passed, ${res.failed} failed`);
      setTimeout(() => setQuickNotice(null), 4000);
    } catch (err) {
      console.error(err);
      setQuickNotice('Failed to run verification');
      setTimeout(() => setQuickNotice(null), 3000);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <header className="h-16 bg-slate-850/90 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <div className="text-sm font-bold text-white tracking-wide">
          AI-Driven Network Intent Verification &amp; Repair Platform
        </div>
        <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
          Deterministic Zero-Trust Simulation
        </span>
      </div>

      <div className="flex items-center space-x-4">
        {quickNotice && (
          <div className="hidden lg:flex items-center gap-1.5 text-xs text-emerald-400 font-mono animate-fadeIn">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>{quickNotice}</span>
          </div>
        )}

        <button
          onClick={handleQuickVerification}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow-sm shadow-cyan-600/30 transition-all disabled:opacity-50"
        >
          {isRunning ? (
            <>
              <RefreshCw className="w-3 h-3 animate-spin" />
              <span>Verifying...</span>
            </>
          ) : (
            <>
              <Play className="w-3 h-3 fill-white" />
              <span>Verify Mesh</span>
            </>
          )}
        </button>

        <div className="flex items-center space-x-2 pl-3 border-l border-slate-800">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse glow-emerald"></div>
          <span className="text-xs text-slate-300 font-mono hidden sm:inline">Simulation Online</span>
        </div>
      </div>
    </header>
  );
};

