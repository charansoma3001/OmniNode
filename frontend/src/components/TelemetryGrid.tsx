/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { NetworkNode } from '../types';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import { Signal, Clock, HardDrive, Cpu, AlertTriangle } from 'lucide-react';

interface TelemetryGridProps {
  nodes: NetworkNode[];
}

export const TelemetryGrid: React.FC<TelemetryGridProps> = ({ nodes }) => {
  // Mock history for sparklines
  const generateHistory = () => Array.from({ length: 10 }, () => ({ value: Math.floor(Math.random() * 100) }));

  return (
    <div className="p-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {nodes.map((node) => (
        <div key={node.id} className="bg-[#0d0d12] border border-[#1e1e24] rounded-lg overflow-hidden flex flex-col group hover:border-emerald-500/30 transition-all duration-300">
          <div className="p-4 border-b border-[#1e1e24] flex items-center justify-between bg-white/[0.02]">
            <div className="flex flex-col">
              <span className="text-[10px] text-zinc-500 font-mono tracking-widest">{node.id}</span>
              <h3 className="text-xs font-bold text-white tracking-tight">{node.name}</h3>
            </div>
            <div className={`px-2 py-0.5 rounded text-[9px] font-bold tracking-widest
              ${node.status === 'ONLINE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                node.status === 'SURGE' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                  'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
              {node.status}
            </div>
          </div>

          <div className="p-4 grid grid-cols-2 gap-4 border-b border-[#1e1e24]">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-[9px] text-zinc-500 font-mono tracking-tighter">
                <Signal className="w-3 h-3" /> VOLTAGE
              </div>
              <div className="text-sm font-mono text-zinc-200">{node.telemetry.voltage}</div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-[9px] text-zinc-500 font-mono tracking-tighter">
                <Clock className="w-3 h-3" /> LOAD MW
              </div>
              <div className="text-sm font-mono text-zinc-200">{node.telemetry.loadMw}</div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-[9px] text-zinc-500 font-mono tracking-tighter">
                <HardDrive className="w-3 h-3" /> GEN MW
              </div>
              <div className="text-sm font-mono text-zinc-200">{node.telemetry.genMw}</div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-[9px] text-zinc-500 font-mono tracking-tighter">
                <Cpu className="w-3 h-3" /> FREQUENCY
              </div>
              <div className="text-sm font-mono text-zinc-200">{node.telemetry.frequency}</div>
            </div>
          </div>

          <div className="h-16 w-full p-2 bg-black/20">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={generateHistory()}>
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={node.status === 'ONLINE' ? '#10b981' : '#ef4444'}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <YAxis hide domain={[0, 100]} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {node.status !== 'NOMINAL' && (
            <div className="px-4 py-2 bg-amber-500/5 border-t border-amber-500/10 flex items-center gap-2">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              <span className="text-[9px] text-amber-500/80 font-mono uppercase tracking-widest">Abnormal Grid State Detected</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
