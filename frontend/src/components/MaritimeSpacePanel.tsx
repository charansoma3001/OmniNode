/**
 * Maritime + Space — Realistic monitoring dashboard
 */

import React, { useState, useEffect, useRef } from 'react';
import { Ship, Satellite, Anchor, Waves, Activity, Navigation, Radio, Thermometer } from 'lucide-react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';

type ViewMode = 'MARITIME' | 'SPACE';

interface MaritimeNode {
    id: string;
    name: string;
    type: 'buoy' | 'ship' | 'relay';
    status: 'NOMINAL' | 'WARNING';
    lat: string;
    lng: string;
    x: number;
    y: number;
    depth?: number;
    heading?: number;
    speed?: number;
    waveH?: number;
    tempC?: number;
    salinity?: number;
}

interface SpaceNode {
    id: string;
    name: string;
    type: 'geo' | 'polar' | 'ground';
    status: 'NOMINAL' | 'WARNING';
    orbit?: string;
    lat: string;
    lng: string;
    x: number;
    y: number;
    altKm?: number;
    linkDb: number;
    bandwidthMbps: number;
    uptimePct: number;
}

const MARITIME_NODES: MaritimeNode[] = [
    { id: 'NS-A', name: 'North Sea Alpha', type: 'buoy', status: 'NOMINAL', lat: '56.0°N', lng: '3.0°E', x: 48, y: 18, depth: 45, waveH: 1.4, tempC: 8.2, salinity: 34.8 },
    { id: 'NS-B', name: 'North Sea Bravo', type: 'buoy', status: 'NOMINAL', lat: '54.5°N', lng: '1.5°E', x: 45, y: 22, depth: 38, waveH: 1.7, tempC: 9.1, salinity: 34.5 },
    { id: 'BAL', name: 'Baltic Gateway', type: 'relay', status: 'NOMINAL', lat: '55.7°N', lng: '12.6°E', x: 56, y: 20, depth: 0, waveH: 0.8, tempC: 6.4, salinity: 12.1 },
    { id: 'MED-W', name: 'Mediterranean West', type: 'buoy', status: 'WARNING', lat: '38.7°N', lng: '0.5°W', x: 42, y: 56, depth: 120, waveH: 2.3, tempC: 18.6, salinity: 38.2 },
    { id: 'MED-E', name: 'Mediterranean East', type: 'buoy', status: 'NOMINAL', lat: '35.3°N', lng: '24.5°E', x: 68, y: 62, depth: 180, waveH: 1.1, tempC: 21.3, salinity: 39.1 },
    { id: 'CHN', name: 'Channel Relay', type: 'relay', status: 'NOMINAL', lat: '50.3°N', lng: '1.0°W', x: 42, y: 30, depth: 0, waveH: 1.9, tempC: 11.5, salinity: 35.0 },
    { id: 'ATL-3', name: 'Atlantic Buoy-3', type: 'buoy', status: 'NOMINAL', lat: '48.5°N', lng: '6.8°W', x: 34, y: 35, depth: 210, waveH: 2.8, tempC: 13.2, salinity: 35.5 },
    { id: 'VES-1', name: 'MV Nordic Star', type: 'ship', status: 'NOMINAL', lat: '53.2°N', lng: '4.1°E', x: 47, y: 24, heading: 215, speed: 12.4 },
    { id: 'VES-2', name: 'MV Poseidon VII', type: 'ship', status: 'NOMINAL', lat: '42.1°N', lng: '10.3°E', x: 54, y: 50, heading: 142, speed: 8.7 },
];

const SPACE_NODES: SpaceNode[] = [
    { id: 'GEO-1', name: 'GEO-SAT-1', type: 'geo', status: 'NOMINAL', orbit: '10°E GEO', lat: '0°', lng: '10°E', x: 52, y: 50, altKm: 35786, linkDb: -112.4, bandwidthMbps: 480, uptimePct: 99.99 },
    { id: 'GEO-2', name: 'GEO-SAT-2', type: 'geo', status: 'NOMINAL', orbit: '25°E GEO', lat: '0°', lng: '25°E', x: 62, y: 50, altKm: 35786, linkDb: -114.1, bandwidthMbps: 420, uptimePct: 99.97 },
    { id: 'POL-N', name: 'POLAR-RELAY-N', type: 'polar', status: 'NOMINAL', orbit: 'Polar LEO', lat: '78°N', lng: '15°E', x: 56, y: 8, altKm: 780, linkDb: -98.2, bandwidthMbps: 120, uptimePct: 99.91 },
    { id: 'POL-S', name: 'POLAR-RELAY-S', type: 'polar', status: 'WARNING', orbit: 'Polar LEO', lat: '71°S', lng: '2°W', x: 44, y: 92, altKm: 780, linkDb: -102.6, bandwidthMbps: 95, uptimePct: 98.44 },
    { id: 'SVB', name: 'Svalbard Ground', type: 'ground', status: 'NOMINAL', lat: '78.2°N', lng: '15.6°E', x: 51, y: 37, altKm: 0, linkDb: -82.1, bandwidthMbps: 1200, uptimePct: 99.95 },
    { id: 'TRM', name: 'Tromsø Station', type: 'ground', status: 'NOMINAL', lat: '69.6°N', lng: '19.0°E', x: 53, y: 41, altKm: 0, linkDb: -79.8, bandwidthMbps: 1400, uptimePct: 99.98 },
];

const jitter = (val: number, range: number) => val + (Math.random() - 0.5) * range;

export const MaritimeSpacePanel: React.FC<{ mode: ViewMode }> = ({ mode }) => {
    const [tick, setTick] = useState(0);
    const [selectedId, setSelectedId] = useState(mode === 'MARITIME' ? 'NS-A' : 'GEO-1');
    const [logEntries, setLogEntries] = useState<string[]>([]);
    const logRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const iv = setInterval(() => setTick(t => t + 1), 2500);
        return () => clearInterval(iv);
    }, []);

    useEffect(() => {
        if (mode === 'MARITIME') {
            const n = MARITIME_NODES[tick % MARITIME_NODES.length];
            const msgs = [
                `[NAV] ${n.id} position fix: ${n.lat}, ${n.lng} — accuracy ±${(0.5 + Math.random() * 1.5).toFixed(1)}m`,
                `[ENV] ${n.id} wave height: ${jitter(n.waveH || 1.5, 0.4).toFixed(1)}m | temp: ${jitter(n.tempC || 15, 2).toFixed(1)}°C`,
                `[COM] ${n.id} relay handshake OK — ${(45 + Math.random() * 30).toFixed(0)}ms RTT`,
            ];
            setLogEntries(prev => [...prev.slice(-40), msgs[tick % msgs.length]]);
        } else {
            const n = SPACE_NODES[tick % SPACE_NODES.length];
            const msgs = [
                `[TLM] ${n.id} link budget: ${jitter(n.linkDb, 2).toFixed(1)} dB — margin +${(2 + Math.random() * 4).toFixed(1)} dB`,
                `[ORB] ${n.id} ephemeris update — Δv: ${(Math.random() * 0.02).toFixed(4)} m/s`,
                `[BW] ${n.id} throughput: ${jitter(n.bandwidthMbps, 30).toFixed(0)} Mbps`,
            ];
            setLogEntries(prev => [...prev.slice(-40), msgs[tick % msgs.length]]);
        }
    }, [tick, mode]);

    useEffect(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
    }, [logEntries]);

    const [worldData, setWorldData] = useState<any>(null);

    // Fetch World Map for Europe Background
    useEffect(() => {
        d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
            .then((data: any) => {
                setWorldData(topojson.feature(data, data.objects.countries));
            });
    }, []);

    const isMaritime = mode === 'MARITIME';

    // Map projection
    const width = 100;
    const height = 100;
    const projection = d3.geoMercator()
        .center([10, 50])
        .scale(180)
        .translate([width / 2, height / 2]);

    const geoPath = d3.geoPath().projection(projection);

    const parseCoord = (c: string) => {
        if (!c) return NaN;
        const val = parseFloat(c);
        return (c.includes('S') || c.includes('W')) ? -val : val;
    };

    const nodes = (isMaritime ? MARITIME_NODES : SPACE_NODES).map(n => {
        if (isMaritime) {
            const [px, py] = projection([parseCoord(n.lng), parseCoord(n.lat)]) || [n.x, n.y];
            return { ...n, x: px, y: py };
        }
        return n;
    });

    const selectedNode = nodes.find(n => n.id === selectedId);

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Top Bar */}
            <div className="px-6 py-4 border-b border-[#1e1e24] flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${isMaritime ? 'bg-cyan-500/10 border-cyan-500/20' : 'bg-purple-500/10 border-purple-500/20'}`}>
                        {isMaritime ? <Ship className="w-5 h-5 text-cyan-400" /> : <Satellite className="w-5 h-5 text-purple-400" />}
                    </div>
                    <div>
                        <h2 className="text-sm font-bold text-white tracking-tight uppercase">
                            {isMaritime ? 'Maritime Corridor Monitoring' : 'Space Segment Control'}
                        </h2>
                        <p className="text-[10px] text-zinc-500 font-mono">
                            {isMaritime ? 'Ocean positioning · Buoy networks · Ship tracking' : 'GEO satellites · Polar relays · Arctic ground stations'}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {isMaritime ? (
                        <>
                            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-cyan-500/10 border border-cyan-500/20 rounded text-[9px] font-mono text-cyan-400">
                                <Waves className="w-3 h-3" /> SEA STATE 3
                            </div>
                            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-mono text-emerald-400">
                                <Navigation className="w-3 h-3" /> GEO ACC ±1.2m
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/10 border border-purple-500/20 rounded text-[9px] font-mono text-purple-400">
                                <Radio className="w-3 h-3" /> LINK MARGIN +4.2dB
                            </div>
                            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-mono text-emerald-400">
                                UPTIME 99.98%
                            </div>
                        </>
                    )}
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Left: Map */}
                <div className="flex-1 flex flex-col min-w-0">
                    <div className="flex-1 relative bg-[#060609] min-h-[280px]">
                        <svg viewBox="0 0 100 100" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
                            {/* Grid */}
                            {Array.from({ length: 20 }, (_, i) => (
                                <line key={`vg${i}`} x1={i * 5} y1="0" x2={i * 5} y2="100" stroke={isMaritime ? '#0a1929' : '#120a29'} strokeWidth="0.15" />
                            ))}
                            {Array.from({ length: 20 }, (_, i) => (
                                <line key={`hg${i}`} x1="0" y1={i * 5} x2="100" y2={i * 5} stroke={isMaritime ? '#0a1929' : '#120a29'} strokeWidth="0.15" />
                            ))}

                            {/* Maritime: Coastline hint arcs */}
                            {isMaritime && (
                                <g>
                                    <defs>
                                        <path id="shipPatrol" d="M 0,-1.5 A 1.5,1.5 0 1,1 0,1.5 A 1.5,1.5 0 1,1 0,-1.5" />
                                    </defs>
                                    {worldData && worldData.features.map((f: any, i: number) => (
                                        <path key={`c${i}`} d={geoPath(f) || ''} fill="#0a1929" stroke="#1a3a5c" strokeWidth="0.2" />
                                    ))}
                                    <text x="30" y="45" fill="#1a3a5c" fontSize="2.5" fontFamily="monospace">ATLANTIC</text>
                                    <text x="50" y="42" fill="#0a293a" fontSize="1.8" fontFamily="monospace">NORTH SEA</text>
                                    <text x="52" y="58" fill="#0a293a" fontSize="1.8" fontFamily="monospace">MEDITERRANEAN</text>
                                </g>
                            )}

                            {/* Space: 3D Earth and Orbit paths */}
                            {!isMaritime && (
                                <g>
                                    <defs>
                                        <radialGradient id="earthGrad" cx="50%" cy="50%" r="50%">
                                            <stop offset="60%" stopColor="#0a1929" />
                                            <stop offset="95%" stopColor="#1a3a5c" />
                                            <stop offset="100%" stopColor="#3b82f6" />
                                        </radialGradient>
                                        <path id="geoPath" d="M 9,50 A 41,12 0 1,0 91,50 A 41,12 0 1,0 9,50" />
                                        <path id="polarPath" d="M 50,9 A 12,41 0 1,0 50,91 A 12,41 0 1,0 50,9" />
                                    </defs>

                                    {/* 3D Earth */}
                                    <circle cx="50" cy="50" r="14" fill="url(#earthGrad)" opacity="0.9" />
                                    {/* Earth grid lines for 3D effect */}
                                    <ellipse cx="50" cy="50" rx="14" ry="4" fill="none" stroke="#3b82f6" strokeWidth="0.1" opacity="0.4" />
                                    <ellipse cx="50" cy="50" rx="14" ry="9" fill="none" stroke="#3b82f6" strokeWidth="0.1" opacity="0.3" />
                                    <ellipse cx="50" cy="50" rx="4" ry="14" fill="none" stroke="#3b82f6" strokeWidth="0.1" opacity="0.4" />
                                    <ellipse cx="50" cy="50" rx="9" ry="14" fill="none" stroke="#3b82f6" strokeWidth="0.1" opacity="0.3" />

                                    {/* GEO Orbit Path */}
                                    <use href="#geoPath" fill="none" stroke="#2a1a5c" strokeWidth="0.3" strokeDasharray="2,2" />
                                    <text x="12" y="60" fill="#2a1a5c" fontSize="1.8" fontFamily="monospace">GEO ORBIT 35,786 km</text>

                                    {/* Polar Orbit Path */}
                                    <use href="#polarPath" fill="none" stroke="#1a2a4c" strokeWidth="0.2" strokeDasharray="1,2" />
                                    <text x="34" y="12" fill="#1a2a4c" fontSize="1.5" fontFamily="monospace">POLAR LEO</text>
                                </g>
                            )}

                            {/* Static Connection lines */}
                            {isMaritime ? (
                                [['NS-A', 'NS-B'], ['NS-B', 'CHN'], ['CHN', 'ATL-3'], ['MED-W', 'MED-E'], ['BAL', 'NS-A'], ['VES-1', 'NS-B']].map(([a, b], i) => {
                                    const na = nodes.find(n => n.id === a)!;
                                    const nb = nodes.find(n => n.id === b)!;
                                    return (
                                        <line key={i} x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                                            stroke="#0e4a6e" strokeWidth="0.25" strokeDasharray="1.5,1.5" className="animate-flow" />
                                    );
                                })
                            ) : (
                                [['SVB', 'TRM']].map(([a, b], i) => {
                                    const na = SPACE_NODES.find(n => n.id === a)!;
                                    const nb = SPACE_NODES.find(n => n.id === b)!;
                                    return (
                                        <line key={i} x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                                            stroke="#3a1a6e" strokeWidth="0.25" strokeDasharray="1.5,1.5" className="animate-flow" />
                                    );
                                })
                            )}

                            {/* Nodes Rendering */}
                            {(nodes as any[]).map((n: any) => {
                                const isSelected = n.id === selectedId;
                                const isShip = n.type === 'ship';
                                const isSpaceMotion = !isMaritime && (n.type === 'geo' || n.type === 'polar');
                                const color = n.status === 'WARNING' ? '#f59e0b' : isMaritime ? '#06b6d4' : '#a855f7';
                                const shapeRadius = isShip ? 1.2 : n.type === 'geo' || n.type === 'polar' ? 1.5 : 1;

                                // Determine orbit path and start delay (slowed down for realism)
                                const motionPathInfo = Object.freeze({
                                    'GEO-1': { path: '#geoPath', dur: '120s', delay: '0s' },
                                    'GEO-2': { path: '#geoPath', dur: '120s', delay: '-60s' },
                                    'POL-N': { path: '#polarPath', dur: '60s', delay: '0s' },
                                    'POL-S': { path: '#polarPath', dur: '60s', delay: '-30s' }
                                } as Record<string, { path: string; dur: string; delay: string }>);

                                const motion = isSpaceMotion ? motionPathInfo[n.id] : null;

                                return (
                                    <g key={n.id} className="cursor-pointer" onClick={() => setSelectedId(n.id)}>
                                        {/* If it's a moving space node, attach animateMotion and set its base to 0,0 */}
                                        {motion && (
                                            <animateMotion dur={motion.dur} begin={motion.delay} repeatCount="indefinite">
                                                <mpath href={motion.path} />
                                            </animateMotion>
                                        )}
                                        {/* Use absolute x,y for static nodes, use 0,0 for space animated nodes */}
                                        <g transform={motion ? `translate(0, 0)` : `translate(${n.x}, ${n.y})`}>
                                            {isShip && (
                                                <animateMotion dur="40s" repeatCount="indefinite">
                                                    <mpath href="#shipPatrol" />
                                                </animateMotion>
                                            )}
                                            <circle cx="0" cy="0" r={shapeRadius + 1.5} fill="none" stroke={color} strokeWidth="0.15" opacity={0.3}>
                                                <animate attributeName="r" from={`${shapeRadius + 0.5}`} to={`${shapeRadius + 4}`} dur="2.5s" repeatCount="indefinite" />
                                                <animate attributeName="opacity" from="0.5" to="0" dur="2.5s" repeatCount="indefinite" />
                                            </circle>
                                            {n.type === 'ship' ? (
                                                <polygon points={`0,-1.5 -1,1 1,1`}
                                                    fill={color} stroke={isSelected ? '#fff' : 'none'} strokeWidth="0.3" />
                                            ) : (
                                                <circle cx="0" cy="0" r={shapeRadius}
                                                    fill={color} stroke={isSelected ? '#fff' : 'none'} strokeWidth={isSelected ? 0.4 : 0} />
                                            )}
                                            <text x={2.5} y={0.5} fill={isSelected ? '#fff' : '#6b7280'} fontSize="1.8" fontFamily="monospace">{n.name}</text>
                                        </g>
                                    </g>
                                );
                            })}
                        </svg>
                    </div>

                    {/* Node Table */}
                    <div className="h-[160px] border-t border-[#1e1e24] overflow-auto">
                        <table className="w-full text-[10px] font-mono">
                            <thead className="sticky top-0 bg-[#0a0a0c]">
                                <tr className="text-zinc-600 border-b border-[#1e1e24]">
                                    <th className="text-left px-4 py-2">NODE</th>
                                    <th className="text-left px-2 py-2">TYPE</th>
                                    <th className="text-left px-2 py-2">STATUS</th>
                                    {isMaritime ? (
                                        <>
                                            <th className="text-right px-2 py-2">WAVE</th>
                                            <th className="text-right px-2 py-2">TEMP</th>
                                            <th className="text-right px-2 py-2">DEPTH</th>
                                        </>
                                    ) : (
                                        <>
                                            <th className="text-right px-2 py-2">ALT (km)</th>
                                            <th className="text-right px-2 py-2">LINK</th>
                                            <th className="text-right px-2 py-2">BW</th>
                                        </>
                                    )}
                                    <th className="text-right px-4 py-2">POS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(nodes as any[]).map((n: any) => (
                                    <tr key={n.id}
                                        onClick={() => setSelectedId(n.id)}
                                        className={`border-b border-[#1e1e24]/50 cursor-pointer transition-colors ${n.id === selectedId ? (isMaritime ? 'bg-cyan-500/5' : 'bg-purple-500/5') : 'hover:bg-white/[0.02]'}`}>
                                        <td className="px-4 py-2 text-white font-medium">{n.name}</td>
                                        <td className="px-2 py-2">
                                            <span className={`text-[9px] px-1.5 py-0.5 rounded ${isMaritime ? 'bg-cyan-500/10 text-cyan-400' : 'bg-purple-500/10 text-purple-400'}`}>
                                                {n.type.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="px-2 py-2">
                                            <span className={`px-1.5 py-0.5 rounded ${n.status === 'WARNING' ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-300'}`}>
                                                {n.status}
                                            </span>
                                        </td>
                                        {isMaritime ? (
                                            <>
                                                <td className="px-2 py-2 text-right text-zinc-300">{n.waveH ? `${jitter(n.waveH, 0.3).toFixed(1)}m` : '—'}</td>
                                                <td className="px-2 py-2 text-right text-zinc-300">{n.tempC ? `${jitter(n.tempC, 1).toFixed(1)}°C` : '—'}</td>
                                                <td className="px-2 py-2 text-right text-zinc-300">{n.depth ? `${n.depth}m` : '—'}</td>
                                            </>
                                        ) : (
                                            <>
                                                <td className="px-2 py-2 text-right text-zinc-300">{n.altKm ? n.altKm.toLocaleString() : '—'}</td>
                                                <td className="px-2 py-2 text-right text-zinc-300">{jitter(n.linkDb, 1.5).toFixed(1)} dB</td>
                                                <td className="px-2 py-2 text-right text-zinc-300">{jitter(n.bandwidthMbps, 20).toFixed(0)} Mbps</td>
                                            </>
                                        )}
                                        <td className="px-4 py-2 text-right text-zinc-500">{n.lat}, {n.lng}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right: Detail + Log */}
                <div className="w-[280px] border-l border-[#1e1e24] flex flex-col shrink-0">
                    {selectedNode && (
                        <div className="p-4 border-b border-[#1e1e24]">
                            <div className="flex items-center gap-2 mb-3">
                                {isMaritime ? <Anchor className="w-3.5 h-3.5 text-cyan-400" /> : <Satellite className="w-3.5 h-3.5 text-purple-400" />}
                                <span className="text-xs font-bold text-white">{(selectedNode as any).name}</span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-[9px] font-mono">
                                {isMaritime ? (
                                    <>
                                        {[
                                            { label: 'Lat/Lng', value: `${selectedNode.lat}` },
                                            { label: 'Type', value: (selectedNode as any).type },
                                            { label: 'Wave Ht', value: `${(selectedNode as MaritimeNode).waveH || '—'}m` },
                                            { label: 'Water Temp', value: `${(selectedNode as MaritimeNode).tempC || '—'}°C` },
                                            { label: 'Depth', value: `${(selectedNode as MaritimeNode).depth || '—'}m` },
                                            { label: 'Salinity', value: `${(selectedNode as MaritimeNode).salinity || '—'} PSU` },
                                        ].map(item => (
                                            <div key={item.label} className="bg-[#0d0d12] border border-[#1e1e24] rounded p-2">
                                                <div className="text-[8px] text-zinc-600 uppercase">{item.label}</div>
                                                <div className="text-zinc-300 mt-0.5">{item.value}</div>
                                            </div>
                                        ))}
                                    </>
                                ) : (
                                    <>
                                        {[
                                            { label: 'Orbit', value: (selectedNode as SpaceNode).orbit || 'Ground' },
                                            { label: 'Altitude', value: (selectedNode as SpaceNode).altKm ? `${(selectedNode as SpaceNode).altKm!.toLocaleString()} km` : 'Surface' },
                                            { label: 'Link Budget', value: `${(selectedNode as SpaceNode).linkDb} dB` },
                                            { label: 'Bandwidth', value: `${(selectedNode as SpaceNode).bandwidthMbps} Mbps` },
                                            { label: 'Uptime', value: `${(selectedNode as SpaceNode).uptimePct}%` },
                                            { label: 'Status', value: selectedNode.status },
                                        ].map(item => (
                                            <div key={item.label} className="bg-[#0d0d12] border border-[#1e1e24] rounded p-2">
                                                <div className="text-[8px] text-zinc-600 uppercase">{item.label}</div>
                                                <div className="text-zinc-300 mt-0.5">{item.value}</div>
                                            </div>
                                        ))}
                                    </>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Live Log */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <div className="px-4 py-2 border-b border-[#1e1e24] flex items-center gap-2">
                            <Activity className="w-3 h-3 text-emerald-500" />
                            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">
                                {isMaritime ? 'Maritime Feed' : 'Space Telemetry'}
                            </span>
                        </div>
                        <div ref={logRef} className="flex-1 overflow-auto p-3 space-y-1">
                            {logEntries.map((msg, i) => (
                                <div key={i} className="text-[9px] font-mono text-zinc-500 leading-relaxed">
                                    <span className="text-zinc-600">{new Date().toLocaleTimeString('en-GB', { hour12: false })}</span>{' '}
                                    <span className="text-zinc-400">{msg}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
