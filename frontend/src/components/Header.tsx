/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Clock, Zap, Activity, AlertTriangle } from 'lucide-react';
import { GridPayload } from '@/hooks/useGridState';

interface HeaderProps {
  gridData: GridPayload | null;
}

export const Header: React.FC<HeaderProps> = ({ gridData }) => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const stats = [
    { label: 'TOTAL GENERATION', value: gridData ? `${gridData.total_generation_mw.toFixed(1)} MW` : 'N/A', icon: Zap, color: 'text-emerald-400' },
    { label: 'FREQUENCY', value: gridData ? `${gridData.frequency_hz.toFixed(2)} Hz` : 'N/A', icon: Activity, color: 'text-blue-400' },
    { label: 'SYSTEM LOSSES', value: gridData ? `${gridData.total_losses_mw.toFixed(2)} MW` : 'N/A', icon: AlertTriangle, color: 'text-amber-400' },
  ];

  return (
    <header className="h-16 bg-[#0a0a0c] border-b border-[#1e1e24] flex items-center justify-between px-8 shrink-0">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-3 text-zinc-400">
          <Clock className="w-4 h-4" />
          <span className="text-xs font-mono tracking-widest uppercase">
            {time.toLocaleTimeString('en-GB', { hour12: false })} UTC
          </span>
        </div>

        <div className="h-4 w-px bg-[#1e1e24]" />

        <div className="flex items-center gap-6">
          {stats.map((stat) => (
            <div key={stat.label} className="flex items-center gap-3">
              <stat.icon className={`w-3.5 h-3.5 ${stat.color} opacity-70`} />
              <div className="flex flex-col">
                <span className="text-[9px] text-zinc-500 font-mono tracking-tighter leading-none mb-0.5">
                  {stat.label}
                </span>
                <span className="text-[11px] text-zinc-200 font-mono leading-none">
                  {stat.value}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded">
          <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
          <span className="text-[10px] font-bold text-emerald-400 tracking-widest uppercase">
            System Nominal
          </span>
        </div>
        <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center">
          <span className="text-[10px] font-bold text-zinc-400">CS</span>
        </div>
      </div>
    </header>
  );
};
