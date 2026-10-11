import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner: React.FC<{ message?: string }> = ({ message = 'Loading...' }) => (
  <div className="flex flex-col items-center justify-center p-8 space-y-4">
    <Loader2 className="w-8 h-8 text-cyan-500 animate-spin" />
    <span className="text-slate-400">{message}</span>
  </div>
);
