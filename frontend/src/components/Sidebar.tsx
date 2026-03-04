/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { LayoutGrid, Globe, Ship, Satellite, Users, Activity, ShieldAlert, MessageSquare } from 'lucide-react';
import { SegmentType } from '../types';

interface SidebarProps {
  activeSegment: SegmentType | 'AGENTS' | 'SIGINT';
  onSegmentChange: (segment: SegmentType | 'AGENTS' | 'SIGINT') => void;
  onToggleChat?: () => void;
  isChatOpen?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeSegment, onSegmentChange, onToggleChat, isChatOpen }) => {
  const items = [
    { id: 'ZONE 1', icon: LayoutGrid, label: 'Zone 1 (Core)' },
    { id: 'ZONE 2', icon: Globe, label: 'Zone 2 (Industrial)' },
    { id: 'ZONE 3', icon: Activity, label: 'Zone 3 (Residential)' },
    { id: 'GLOBAL', icon: Globe, label: 'Global Grid View' },
    { id: 'divider', type: 'divider' },
    { id: 'AGENTS', icon: Users, label: 'Agent Orchestrator' },
    { id: 'SIGINT', icon: ShieldAlert, label: 'Guardian Intercept' },
    { id: 'divider2', type: 'divider' },
    { id: 'CHAT', icon: MessageSquare, label: 'AI Analyst' },
  ];

  return (
    <nav className="w-64 bg-[#0a0a0c] border-r border-[#1e1e24] flex flex-col h-full">
      <div className="p-6 border-b border-[#1e1e24]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500/20 border border-emerald-500/40 rounded flex items-center justify-center">
            <Activity className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wider text-white">OMNINODE</h1>
            <p className="text-[10px] text-zinc-500 font-mono">MISSION CONTROL v1.0</p>
          </div>
        </div>
      </div>

      <div className="flex-1 py-4 overflow-y-auto">
        {items.map((item, idx) => {
          if (item.type === 'divider') {
            return <div key={idx} className="my-4 mx-6 border-t border-[#1e1e24]" />;
          }

          const Icon = item.icon!;
          const isChat = item.id === 'CHAT';
          const isActive = isChat ? !!isChatOpen : activeSegment === item.id;

          return (
            <button
              key={item.id}
              onClick={() => isChat ? onToggleChat?.() : onSegmentChange(item.id as any)}
              className={`w-full flex items-center gap-3 px-6 py-3 text-sm transition-all duration-200 group
                ${isActive
                  ? 'text-emerald-400 bg-emerald-500/5 border-r-2 border-emerald-500'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'}`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500 group-hover:text-zinc-300'}`} />
              <span className="font-medium tracking-tight">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="p-6 border-t border-[#1e1e24]">
        <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 mb-2">
          <span>SYSTEM UPLINK</span>
          <span className="text-emerald-500">ACTIVE</span>
        </div>
        <div className="w-full bg-zinc-900 h-1 rounded-full overflow-hidden">
          <div className="bg-emerald-500 h-full w-3/4 animate-pulse" />
        </div>
      </div>
    </nav>
  );
};
