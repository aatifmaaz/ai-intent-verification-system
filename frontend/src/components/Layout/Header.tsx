import React, { useState } from 'react';
import { Play, CheckCircle, RefreshCw, Zap, Sparkles } from 'lucide-react';
import { runVerification } from '../../api/verification';
import { AutoPilotModal } from '../AutoPilotModal';

export const Header: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [quickNotice, setQuickNotice] = useState<string | null>(null);
  const [isAutoPilotOpen, setIsAutoPilotOpen] = useState(false);
  const [headerPrompt, setHeaderPrompt] = useState('');

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

  const handleQuickAutoPilotSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsAutoPilotOpen(true);
  };

  return (
    <>
      <header className="h-16 bg-slate-850/90 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-40 gap-4">
        {/* Left: Title & Badge */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            AI Network Intent Verification
          </div>
          <span className="hidden xl:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            Autonomous Zero-Trust
          </span>
        </div>

        {/* Middle: Prominent Global Plain-English AI Command Bar */}
        <form 
          onSubmit={handleQuickAutoPilotSubmit}
          className="flex-1 max-w-xl mx-2 hidden md:flex items-center relative group"
        >
          <div className="absolute left-3 text-cyan-400 flex items-center pointer-events-none">
            <Sparkles className="w-4 h-4 animate-pulse" />
          </div>
          <input
            type="text"
            value={headerPrompt}
            onChange={(e) => setHeaderPrompt(e.target.value)}
            placeholder="Type any plain English requirement (e.g. 'Stop guest from reaching HR')..."
            className="w-full pl-9 pr-24 py-1.5 bg-slate-950/80 hover:bg-slate-950 border border-slate-700/80 focus:border-cyan-500 rounded-lg text-xs font-mono text-cyan-300 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-all shadow-inner"
          />
          <button
            type="submit"
            className="absolute right-1 px-2.5 py-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-[11px] font-bold rounded-md flex items-center gap-1 shadow-sm transition-all"
          >
            <Zap className="w-3 h-3 fill-white" />
            Auto-Enforce
          </button>
        </form>

        {/* Right Action Buttons */}
        <div className="flex items-center space-x-3 flex-shrink-0">
          {/* Mobile Auto-Pilot Trigger Button */}
          <button
            onClick={() => setIsAutoPilotOpen(true)}
            className="flex md:hidden items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow-sm"
          >
            <Zap className="w-3 h-3 fill-white" />
            <span>Auto-Pilot</span>
          </button>

          {quickNotice && (
            <div className="hidden lg:flex items-center gap-1.5 text-xs text-emerald-400 font-mono animate-fadeIn">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>{quickNotice}</span>
            </div>
          )}

          <button
            onClick={handleQuickVerification}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 shadow-sm transition-all disabled:opacity-50"
            title="Run complete graph reachability verification"
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
                <span>Verifying...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-slate-300" />
                <span>Verify Mesh</span>
              </>
            )}
          </button>

          <div className="flex items-center space-x-2 pl-3 border-l border-slate-800">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse glow-emerald"></div>
            <span className="text-xs text-slate-300 font-mono hidden sm:inline">Engine Active</span>
          </div>
        </div>
      </header>

      {/* Global Autonomous AutoPilot Modal */}
      <AutoPilotModal
        isOpen={isAutoPilotOpen}
        onClose={() => setIsAutoPilotOpen(false)}
        defaultPrompt={headerPrompt || "Stop guest from reaching HR"}
        onSuccess={() => {
          setQuickNotice("Autonomous requirement successfully enforced!");
          setTimeout(() => setQuickNotice(null), 5000);
        }}
      />
    </>
  );
};


