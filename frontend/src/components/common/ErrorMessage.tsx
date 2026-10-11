import React from 'react';

export const ErrorMessage: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="card p-6 border-red-500/30 bg-red-500/5 text-center">
    <div className="text-red-400 mb-2 font-semibold">Error Loading Data</div>
    <div className="text-slate-400 text-sm mb-4">{message}</div>
    {onRetry && (
      <button 
        onClick={onRetry}
        className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-md text-sm transition-colors"
      >
        Try Again
      </button>
    )}
  </div>
);
