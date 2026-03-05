/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Agent } from '../types';
import { Shield, Zap, Cpu, Activity, ArrowRight } from 'lucide-react';

interface AgentCardProps {
  agent: Agent;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent }) => (
  <div className={`p-4 bg-[#0d0d12] border border-[#1e1e24] rounded-lg shadow-lg hover:border-emerald-500/50 transition-all duration-300 group relative overflow-hidden`}>
    <div className="absolute top-0 right-0 w-12 h-12 bg-emerald-500/5 rotate-45 translate-x-6 -translate-y-6 group-hover:bg-emerald-500/10 transition-colors" />
    
    <div className="flex items-start justify-between mb-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center border
          ${agent.hierarchyLevel === 0 ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400' : 
            agent.hierarchyLevel === 1 ? 'bg-blue-500/20 border-blue-500/40 text-blue-400' : 
            'bg-zinc-500/20 border-zinc-500/40 text-zinc-400'}`}>
          {agent.hierarchyLevel === 0 ? <Shield className="w-5 h-5" /> : 
           agent.hierarchyLevel === 1 ? <Zap className="w-5 h-5" /> : 
           <Cpu className="w-5 h-5" />}
        </div>
        <div>
          <h3 className="text-sm font-bold text-white tracking-tight leading-none mb-1">{agent.name}</h3>
          <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-widest">{agent.role}</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
        <div className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse" />
        <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-tighter">{agent.status}</span>
      </div>
    </div>

    {agent.embodiment && (
      <div className="mb-4 p-2 bg-zinc-900/50 border border-zinc-800 rounded flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-3 h-3 text-zinc-500" />
          <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Embodied System</span>
        </div>
        <span className="text-[10px] text-emerald-400 font-mono font-bold">{agent.embodiment}</span>
      </div>
    )}

    <div className="space-y-2">
      <div className="text-[9px] text-zinc-500 font-mono uppercase tracking-widest mb-1">Active Tasks</div>
      {agent.tasks.map((task, idx) => (
        <div key={idx} className="flex items-center gap-2 text-[11px] text-zinc-300">
          <ArrowRight className="w-3 h-3 text-emerald-500/50" />
          <span>{task}</span>
        </div>
      ))}
    </div>
  </div>
);

interface AgentOrchestratorProps {
  agents: Agent[];
}

export const AgentOrchestrator: React.FC<AgentOrchestratorProps> = ({ agents }) => {
  const orchestrator = agents.find(a => a.hierarchyLevel === 0);
  const segments = agents.filter(a => a.hierarchyLevel === 1);
  const nodes = agents.filter(a => a.hierarchyLevel === 2);

  return (
    <div className="p-8 space-y-12 max-w-7xl mx-auto">
      <div className="flex flex-col items-center">
        <div className="text-[10px] font-mono text-emerald-500 tracking-[0.3em] uppercase mb-4">Level 0: Global Orchestrator</div>
        {orchestrator && <div className="w-80"><AgentCard agent={orchestrator} /></div>}
        <div className="h-12 w-px bg-emerald-500/20 my-2" />
      </div>

      <div className="space-y-4">
        <div className="text-[10px] font-mono text-blue-500 tracking-[0.3em] uppercase text-center mb-8">Level 1: Segment Controllers</div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {segments.map(agent => (
            <div key={agent.id} className="relative">
              <AgentCard agent={agent} />
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <div className="text-[10px] font-mono text-zinc-500 tracking-[0.3em] uppercase text-center mb-8">Level 2: Node Controllers (Embodied)</div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {nodes.map(agent => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      </div>
    </div>
  );
};
