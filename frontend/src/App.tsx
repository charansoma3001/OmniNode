/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { TelemetryGrid } from './components/TelemetryGrid';
import { AgentOrchestrator } from './components/AgentOrchestrator';
import { NetworkMap } from './components/NetworkMap';
import { GeographicCoverageMap } from './components/GeographicCoverageMap';
import { BrainScanner } from './components/BrainScanner';
import { GuardianPanel } from './components/GuardianPanel';
import { ChatPanel } from './components/ChatPanel';
import { DomainPlaceholder } from './components/DomainPlaceholder';
import { DomesticGroundPanel } from './components/DomesticGroundPanel';
import { MaritimeSpacePanel } from './components/MaritimeSpacePanel';
import { PiGnnPanel } from './components/PiGnnPanel';
import { INITIAL_AGENTS } from './constants';
import { NetworkNode, SegmentType } from './types';
import { useGridState } from '@/hooks/useGridState';
import useWebSocket from 'react-use-websocket';
import { wsUrl } from '@/lib/config';

export default function App() {
  const [activeSegment, setActiveSegment] = useState<string>('ZONE 1');
  const [geoFilter, setGeoFilter] = useState<SegmentType | 'ALL'>('ALL');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [surgeActive, setSurgeActive] = useState(false);

  const { gridData } = useGridState();

  // Command WebSocket for surge/rollback
  const { sendMessage: sendCommand } = useWebSocket(wsUrl('/ws/commands'), {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
    share: true, // Share the same connection with ChatPanel
  });

  const handleSurgeToggle = useCallback(() => {
    if (!surgeActive) {
      // Trigger peak_load scenario
      sendCommand(JSON.stringify({ action: 'trigger_scenario', payload: 'line_overload' }));
      setSurgeActive(true);
    } else {
      // Rollback
      sendCommand(JSON.stringify({ action: 'rollback', payload: null }));
      setSurgeActive(false);
    }
  }, [surgeActive, sendCommand]);

  // Map backend gridData to the frontend NetworkNode format
  const activeNodes: NetworkNode[] = React.useMemo(() => {
    if (!gridData) return [];
    return gridData.nodes.map(node => {
      const isCritical = node.vm_pu < 0.90 || node.vm_pu > 1.10;
      const isWarning = node.vm_pu < 0.95 || node.vm_pu > 1.05;
      const status = isCritical ? 'CRITICAL' : isWarning ? 'WARNING' : 'NOMINAL';

      // Backend sends 'zone1', frontend uses 'ZONE 1'
      const zoneNum = node.zone.replace('zone', '');

      return {
        id: `Bus-${node.id}`,
        name: `Substation ${node.id}`,
        type: (zoneNum ? `ZONE ${zoneNum}` : 'GLOBAL') as SegmentType,
        status,
        location: { lat: 40 + node.y * 2, lng: -100 + node.x * 2 },
        telemetry: {
          voltage: `${node.vm_pu.toFixed(3)} pu`,
          loadMw: 'N/A',
          genMw: 'N/A',
          frequency: `${gridData.frequency_hz.toFixed(2)} Hz`,
        }
      };
    });
  }, [gridData]);

  // Domain-specific overlay nodes for the Geographic Coverage Map
  const DOMAIN_NODES: NetworkNode[] = [
    // DOMESTIC ground stations
    { id: 'DOM-LON', name: 'London Hub', type: 'DOMESTIC' as any, status: 'NOMINAL', location: { lat: 51.5, lng: -0.1 }, telemetry: { signalStrength: 98, latency: 8, bandwidth: 10, cpuLoad: 22 } },
    { id: 'DOM-PAR', name: 'Paris Relay', type: 'DOMESTIC' as any, status: 'NOMINAL', location: { lat: 48.9, lng: 2.3 }, telemetry: { signalStrength: 96, latency: 11, bandwidth: 8, cpuLoad: 30 } },
    { id: 'DOM-BER', name: 'Berlin Station', type: 'DOMESTIC' as any, status: 'NOMINAL', location: { lat: 52.5, lng: 13.4 }, telemetry: { signalStrength: 94, latency: 14, bandwidth: 8, cpuLoad: 18 } },
    { id: 'DOM-AMS', name: 'Amsterdam Core', type: 'DOMESTIC' as any, status: 'NOMINAL', location: { lat: 52.4, lng: 4.9 }, telemetry: { signalStrength: 97, latency: 9, bandwidth: 12, cpuLoad: 25 } },
    { id: 'DOM-MAD', name: 'Madrid Gateway', type: 'DOMESTIC' as any, status: 'NOMINAL', location: { lat: 40.4, lng: -3.7 }, telemetry: { signalStrength: 91, latency: 18, bandwidth: 6, cpuLoad: 35 } },
    // OVERSEAS outposts
    { id: 'OVR-WAR', name: 'Warsaw Outpost', type: 'OVERSEAS' as any, status: 'NOMINAL', location: { lat: 52.2, lng: 21.0 }, telemetry: { signalStrength: 88, latency: 24, bandwidth: 4, cpuLoad: 40 } },
    { id: 'OVR-IST', name: 'Istanbul Station', type: 'OVERSEAS' as any, status: 'WARNING', location: { lat: 41.0, lng: 29.0 }, telemetry: { signalStrength: 82, latency: 32, bandwidth: 3, cpuLoad: 55 } },
    { id: 'OVR-ATH', name: 'Athens Relay', type: 'OVERSEAS' as any, status: 'NOMINAL', location: { lat: 37.9, lng: 23.7 }, telemetry: { signalStrength: 86, latency: 28, bandwidth: 4, cpuLoad: 42 } },
    // MARITIME buoys & ships
    { id: 'MAR-NS', name: 'North Sea Alpha', type: 'MARITIME' as any, status: 'NOMINAL', location: { lat: 56.0, lng: 3.0 }, telemetry: { signalStrength: 78, latency: 45, bandwidth: 2, cpuLoad: 12 } },
    { id: 'MAR-BAL', name: 'Baltic Gateway', type: 'MARITIME' as any, status: 'NOMINAL', location: { lat: 55.7, lng: 12.6 }, telemetry: { signalStrength: 80, latency: 42, bandwidth: 2, cpuLoad: 15 } },
    { id: 'MAR-MEDW', name: 'Mediterranean West', type: 'MARITIME' as any, status: 'WARNING', location: { lat: 38.7, lng: -0.5 }, telemetry: { signalStrength: 72, latency: 55, bandwidth: 1.5, cpuLoad: 20 } },
    { id: 'MAR-MEDE', name: 'Mediterranean East', type: 'MARITIME' as any, status: 'NOMINAL', location: { lat: 35.3, lng: 24.5 }, telemetry: { signalStrength: 76, latency: 48, bandwidth: 2, cpuLoad: 18 } },
    { id: 'MAR-VES1', name: 'MV Nordic Star', type: 'MARITIME' as any, status: 'NOMINAL', location: { lat: 53.2, lng: 4.1 }, telemetry: { signalStrength: 70, latency: 60, bandwidth: 1, cpuLoad: 10 } },
    // SPACE ground stations
    { id: 'SPC-SVB', name: 'Svalbard Ground', type: 'SPACE' as any, status: 'NOMINAL', location: { lat: 78.2, lng: 15.6 }, telemetry: { signalStrength: 95, latency: 120, bandwidth: 1.2, cpuLoad: 8 } },
    { id: 'SPC-TRM', name: 'Tromsø Station', type: 'SPACE' as any, status: 'NOMINAL', location: { lat: 69.6, lng: 19.0 }, telemetry: { signalStrength: 92, latency: 110, bandwidth: 1.2, cpuLoad: 10 } },
  ];

  const allCoverageNodes = React.useMemo(() => [...activeNodes, ...DOMAIN_NODES], [activeNodes]);

  const filteredNodes = typeof activeSegment === 'string' && ['ZONE 1', 'ZONE 2', 'ZONE 3', 'GLOBAL'].includes(activeSegment)
    ? (activeSegment === 'GLOBAL' ? activeNodes : activeNodes.filter(node => node.type === activeSegment))
    : activeNodes;

  return (
    <div className="flex h-screen bg-[#050507] text-zinc-200 overflow-hidden font-sans">
      <Sidebar activeSegment={activeSegment} onSegmentChange={setActiveSegment} onToggleChat={() => setIsChatOpen(prev => !prev)} isChatOpen={isChatOpen} />

      <div className="flex-1 flex flex-col min-w-0 transition-all duration-300">
        <Header gridData={gridData} />

        <main className="flex-1 overflow-y-auto bg-[#050507] relative">
          {/* Background Grid Pattern */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e1e24_1px,transparent_1px),linear-gradient(to_bottom,#1e1e24_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-[0.03] pointer-events-none" />

          <div className="relative z-10 h-full">
            {activeSegment === 'AGENTS' ? (
              <AgentOrchestrator agents={INITIAL_AGENTS} />
            ) : activeSegment === 'SIGINT' ? (
              <div className="p-8 h-full max-w-5xl mx-auto"><GuardianPanel /></div>
            ) : activeSegment === 'DOMESTIC' ? (
              <DomesticGroundPanel />
            ) : activeSegment === 'MARITIME' || activeSegment === 'SPACE' ? (
              <MaritimeSpacePanel mode={activeSegment as any} />
            ) : activeSegment === 'PIGNN' ? (
              <PiGnnPanel />
            ) : activeSegment === 'GEOGRAPHIC' ? (
              <div className="p-8 h-full flex flex-col gap-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-white tracking-tight uppercase">Global Geographic Coverage</h2>
                    <p className="text-xs text-zinc-500 font-mono mt-1">Line-of-Sight analysis and blind spot detection</p>
                  </div>
                  <div className="flex items-center gap-2 bg-[#0d0d12] border border-[#1e1e24] p-1 rounded">
                    {['ALL', 'DOMESTIC', 'OVERSEAS', 'MARITIME', 'SPACE'].map((f) => (
                      <button
                        key={f}
                        onClick={() => setGeoFilter(f as any)}
                        className={`px-3 py-1 text-[10px] font-mono rounded transition-colors
                          ${geoFilter === f ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'text-zinc-500 hover:text-zinc-300'}`}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex-1 min-h-[500px]">
                  <GeographicCoverageMap nodes={allCoverageNodes} activeSegment={geoFilter} />
                </div>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                <div className="h-[400px] border-b border-[#1e1e24] relative">
                  {/* Power Grid Overlay */}
                  <div className="absolute top-4 right-4 z-10 bg-black/70 backdrop-blur-sm border border-[#1e1e24] rounded-lg p-3 space-y-2">
                    <div className="text-[8px] font-mono text-zinc-500 uppercase tracking-widest mb-1">System Overview</div>
                    <div className="flex items-center justify-between gap-6">
                      <span className="text-[9px] text-zinc-500 font-mono">TOTAL GENERATION</span>
                      <span className="text-[10px] font-mono font-bold text-emerald-400">{gridData ? `${gridData.total_generation_mw.toFixed(1)} MW` : 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between gap-6">
                      <span className="text-[9px] text-zinc-500 font-mono">FREQUENCY</span>
                      <span className="text-[10px] font-mono font-bold text-blue-400">{gridData ? `${gridData.frequency_hz.toFixed(2)} Hz` : 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between gap-6">
                      <span className="text-[9px] text-zinc-500 font-mono">SYSTEM LOSSES</span>
                      <span className="text-[10px] font-mono font-bold text-amber-400">{gridData ? `${gridData.total_losses_mw.toFixed(2)} MW` : 'N/A'}</span>
                    </div>
                  </div>
                  <NetworkMap
                    nodes={filteredNodes}
                    activeSegment={activeSegment}
                    edges={gridData?.edges}
                  />
                </div>
                <div className="flex-1">
                  <div className="px-8 pt-8 flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-bold text-white tracking-tight uppercase">
                        {activeSegment} Segment Telemetry
                      </h2>
                      <p className="text-xs text-zinc-500 font-mono mt-1">
                        Real-time monitoring of {filteredNodes.length} active nodes
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${surgeActive ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} />
                        <span className="text-[10px] font-mono text-zinc-400 uppercase">
                          {surgeActive ? 'SURGE ACTIVE — PEAK LOAD' : 'Surge Capacity: Nominal'}
                        </span>
                      </div>
                      <button
                        onClick={handleSurgeToggle}
                        className={`px-4 py-1.5 border rounded text-[10px] font-bold transition-colors uppercase tracking-widest ${surgeActive
                          ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                          : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                          }`}
                      >
                        {surgeActive ? '⟲ Rollback' : '⚡ Initiate Surge'}
                      </button>
                    </div>
                  </div>
                  <TelemetryGrid nodes={filteredNodes} />
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* AI Analyst Side Panel (Push Content instead of Overlay) */}
      <div className={`flex flex-col bg-[#050507] border-l border-[#1e1e24] transition-all duration-300 overflow-hidden ${isChatOpen ? 'w-[450px]' : 'w-0 border-l-0'}`}>
        {isChatOpen && (
          <div className="flex flex-col h-full">
            <div className="flex-1 border-b border-[#1e1e24] overflow-hidden relative p-4 flex flex-col">
              <div className="text-[10px] font-mono text-emerald-500 tracking-widest uppercase mb-2">Live Agent Intercepts</div>
              <div className="flex-1 overflow-hidden relative">
                <BrainScanner />
              </div>
            </div>
            <div className="h-1/3 min-h-[250px] overflow-hidden">
              <ChatPanel isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
