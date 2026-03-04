/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Clock, Zap, Activity, AlertTriangle, Github, Radio, Globe, Cpu } from 'lucide-react';
import { GridPayload } from '@/hooks/useGridState';

interface HeaderProps {
  gridData: GridPayload | null;
}

export const Header: React.FC<HeaderProps> = ({ gridData }) => {
  const [time, setTime] = useState(new Date());
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => { setTime(new Date()); setTick(t => t + 1); }, 1000);
    return () => clearInterval(timer);
  }, []);

  const jitter = (base: number, range: number) => base + (Math.random() - 0.5) * range;

  const stats = [
    { label: 'UPLINK LATENCY', value: `${Math.round(jitter(42, 8))}ms`, icon: Radio, color: 'text-cyan-400' },
    { label: 'GLOBAL BANDWIDTH', value: `${jitter(14.2, 1.2).toFixed(1)} Tbps`, icon: Globe, color: 'text-purple-400' },
    { label: 'ORCHESTRATOR LOAD', value: `${Math.round(jitter(28, 6))}%`, icon: Cpu, color: 'text-pink-400' },
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
        <a
          href="https://github.com/charansoma/OmniNode"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center w-8 h-8 rounded bg-[#0d0d12] border border-[#1e1e24] text-zinc-500 hover:text-white hover:border-zinc-500 transition-colors"
        >
          <Github className="w-4 h-4" />
        </a>
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
