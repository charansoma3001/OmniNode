/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  LayoutGrid, Globe, Ship, Satellite, Users, Activity, ShieldAlert,
  MessageSquare, ChevronDown, ChevronRight, Cpu, Waves, Network, Radio, Zap, Brain
} from 'lucide-react';
import { SegmentType } from '../types';

interface SidebarProps {
  activeSegment: SegmentType | 'AGENTS' | 'SIGINT' | 'GEOGRAPHIC' | 'DOMESTIC' | 'MARITIME' | 'SPACE' | 'PIGNN';
  onSegmentChange: (segment: any) => void;
  onToggleChat?: () => void;
  isChatOpen?: boolean;
}

interface SidebarGroup {
  id: string;
  label: string;
  icon: React.ElementType;
  description: string;
  items: { id: string; icon: React.ElementType; label: string }[];
}

export const Sidebar: React.FC<SidebarProps> = ({ activeSegment, onSegmentChange, onToggleChat, isChatOpen }) => {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['digital-twin']));

  const groups: SidebarGroup[] = [
    {
      id: 'digital-twin',
      label: 'Digital Twin',
      icon: Cpu,
      description: 'IEEE 30-Bus Power Grid + PI-GNN',
      items: [
        { id: 'ZONE 1', icon: LayoutGrid, label: 'Zone 1 — Core Hub' },
        { id: 'ZONE 2', icon: Network, label: 'Zone 2 — Industrial' },
        { id: 'ZONE 3', icon: Activity, label: 'Zone 3 — Residential' },
        { id: 'GLOBAL', icon: Globe, label: 'Global Grid View' },
        { id: 'PIGNN', icon: Brain, label: 'PI-GNN Surrogate' },
      ],
    },
    {
      id: 'domestic',
      label: 'Domestic Ground',
      icon: Radio,
      description: '11 sensor servers · 5 actuator servers',
      items: [
        { id: 'DOMESTIC', icon: Zap, label: 'Ground Stations' },
        { id: 'GEOGRAPHIC', icon: Globe, label: 'Coverage Map' },
      ],
    },
    {
      id: 'maritime-space',
      label: 'Maritime + Space',
      icon: Satellite,
      description: 'Ocean corridors · Satellite relays',
      items: [
        { id: 'MARITIME', icon: Ship, label: 'Maritime Corridor' },
        { id: 'SPACE', icon: Satellite, label: 'Space Segment' },
      ],
    },
  ];

  const systemItems = [
    { id: 'AGENTS', icon: Users, label: 'Agent Orchestrator' },
    { id: 'SIGINT', icon: ShieldAlert, label: 'Guardian Intercept' },
    { id: 'CHAT', icon: MessageSquare, label: 'AI Analyst' },
  ];

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  // Check if any child in a group is active
  const groupIsActive = (group: SidebarGroup) =>
    group.items.some(item => activeSegment === item.id);

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

      <div className="flex-1 py-2 overflow-y-auto">
        {/* Section label */}
        <div className="px-6 pt-3 pb-1">
          <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-zinc-600">Domains</span>
        </div>

        {/* Collapsible domain groups */}
        {groups.map(group => {
          const isExpanded = expandedGroups.has(group.id);
          const isGroupActive = groupIsActive(group);
          const GroupIcon = group.icon;

          return (
            <div key={group.id} className="mb-0.5">
              {/* Group header */}
              <button
                onClick={() => toggleGroup(group.id)}
                className={`w-full flex items-center gap-2.5 px-5 py-2 text-left transition-colors group
                  ${isGroupActive ? 'text-emerald-400' : 'text-zinc-400 hover:text-zinc-200'}`}
              >
                {isExpanded
                  ? <ChevronDown className="w-3 h-3 text-zinc-600" />
                  : <ChevronRight className="w-3 h-3 text-zinc-600" />
                }
                <GroupIcon className={`w-4 h-4 ${isGroupActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
                <div className="flex-1 min-w-0">
                  <span className="text-[11px] font-semibold tracking-tight block">{group.label}</span>
                  <span className="text-[8px] font-mono text-zinc-600 block truncate">{group.description}</span>
                </div>
              </button>

              {/* Expanded children */}
              {isExpanded && (
                <div className="ml-3">
                  {group.items.map(item => {
                    const Icon = item.icon;
                    const isActive = activeSegment === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => onSegmentChange(item.id)}
                        className={`w-full flex items-center gap-2.5 pl-7 pr-4 py-1.5 text-[11px] transition-all duration-150
                          ${isActive
                            ? 'text-emerald-400 bg-emerald-500/5 border-r-2 border-emerald-500'
                            : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.02]'}`}
                      >
                        <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-zinc-600'}`} />
                        <span className="font-medium tracking-tight">{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {/* Divider */}
        <div className="my-3 mx-6 border-t border-[#1e1e24]" />

        {/* Section label */}
        <div className="px-6 pb-1">
          <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-zinc-600">System</span>
        </div>

        {/* System items */}
        {systemItems.map(item => {
          const Icon = item.icon;
          const isChat = item.id === 'CHAT';
          const isActive = isChat ? !!isChatOpen : activeSegment === item.id;

          return (
            <button
              key={item.id}
              onClick={() => isChat ? onToggleChat?.() : onSegmentChange(item.id)}
              className={`w-full flex items-center gap-3 px-6 py-2.5 text-[11px] transition-all duration-200 group
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
