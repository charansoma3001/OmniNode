/**
 * Domestic Ground Stations — Realistic monitoring dashboard
 */

import React, { useState, useEffect, useRef } from 'react';
import { Radio, Signal, Wifi, Activity, MapPin, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';

interface Station {
    id: string;
    name: string;
    city: string;
    status: 'NOMINAL' | 'WARNING' | 'CRITICAL';
    lat: string;
    lng: string;
    x: number; // SVG position (% of width)
    y: number; // SVG position (% of height)
    sensors: number;
    actuators: number;
    signalDb: number;
    latencyMs: number;
    uptimePct: number;
    voltage: number;
    frequency: number;
}

const STATIONS: Station[] = [
    { id: 'LDN', name: 'London Hub', city: 'London', status: 'NOMINAL', lat: '51.5°N', lng: '0.1°W', x: 42, y: 28, sensors: 3, actuators: 1, signalDb: -42, latencyMs: 8, uptimePct: 99.97, voltage: 1.002, frequency: 50.01 },
    { id: 'PAR', name: 'Paris Relay', city: 'Paris', status: 'NOMINAL', lat: '48.9°N', lng: '2.3°E', x: 45, y: 38, sensors: 2, actuators: 1, signalDb: -38, latencyMs: 11, uptimePct: 99.94, voltage: 0.998, frequency: 50.00 },
    { id: 'BER', name: 'Berlin Station', city: 'Berlin', status: 'NOMINAL', lat: '52.5°N', lng: '13.4°E', x: 56, y: 30, sensors: 2, actuators: 1, signalDb: -45, latencyMs: 14, uptimePct: 99.91, voltage: 1.001, frequency: 49.99 },
    { id: 'AMS', name: 'Amsterdam Core', city: 'Amsterdam', status: 'NOMINAL', lat: '52.4°N', lng: '4.9°E', x: 47, y: 26, sensors: 1, actuators: 1, signalDb: -36, latencyMs: 9, uptimePct: 99.99, voltage: 1.003, frequency: 50.02 },
    { id: 'BRU', name: 'Brussels Node', city: 'Brussels', status: 'WARNING', lat: '50.8°N', lng: '4.4°E', x: 46, y: 32, sensors: 1, actuators: 0, signalDb: -58, latencyMs: 23, uptimePct: 98.72, voltage: 0.961, frequency: 49.97 },
    { id: 'MAD', name: 'Madrid Gateway', city: 'Madrid', status: 'NOMINAL', lat: '40.4°N', lng: '3.7°W', x: 38, y: 58, sensors: 1, actuators: 1, signalDb: -41, latencyMs: 18, uptimePct: 99.88, voltage: 0.999, frequency: 50.01 },
    { id: 'ROM', name: 'Rome Relay', city: 'Rome', status: 'NOMINAL', lat: '41.9°N', lng: '12.5°E', x: 55, y: 55, sensors: 1, actuators: 0, signalDb: -44, latencyMs: 16, uptimePct: 99.85, voltage: 0.997, frequency: 50.00 },
    { id: 'WAR', name: 'Warsaw Extended', city: 'Warsaw', status: 'NOMINAL', lat: '52.2°N', lng: '21.0°E', x: 63, y: 30, sensors: 1, actuators: 0, signalDb: -52, latencyMs: 22, uptimePct: 99.78, voltage: 1.004, frequency: 49.98 },
];

// Generate fake sparkline data
const genSparkline = (base: number, variance: number, len: number) =>
    Array.from({ length: len }, () => base + (Math.random() - 0.5) * variance);

export const DomesticGroundPanel: React.FC = () => {
    const [tick, setTick] = useState(0);
    const [selected, setSelected] = useState<string>('LDN');
    const [telemetryLog, setTelemetryLog] = useState<string[]>([]);
    const logRef = useRef<HTMLDivElement>(null);
    const [worldData, setWorldData] = useState<any>(null);

    // Fetch World Map for Europe Background
    useEffect(() => {
        d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
            .then((data: any) => {
                setWorldData(topojson.feature(data, data.objects.countries));
            });
    }, []);

    // Tick every 2s to update "live" values
    useEffect(() => {
        const iv = setInterval(() => setTick(t => t + 1), 2000);
        return () => clearInterval(iv);
    }, []);

    // Add fake telemetry log entries
    useEffect(() => {
        const msgs = [
            `[SIG] ${STATIONS[tick % 8].id} signal quality: ${(-30 - Math.random() * 30).toFixed(1)} dBm`,
            `[PWR] ${STATIONS[(tick + 3) % 8].id} voltage: ${(0.98 + Math.random() * 0.04).toFixed(3)} pu`,
            `[NET] ${STATIONS[(tick + 5) % 8].id} latency: ${(5 + Math.random() * 20).toFixed(0)} ms`,
            `[MON] Heartbeat OK — all ${STATIONS.length} stations reporting`,
        ];
        setTelemetryLog(prev => [...prev.slice(-30), msgs[tick % msgs.length]]);
    }, [tick]);

    useEffect(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
    }, [telemetryLog]);

    const selectedStation = STATIONS.find(s => s.id === selected)!;
    const jitter = (val: number, range: number) => (val + (Math.random() - 0.5) * range);

    // Setup map projection
    const width = 100;
    const height = 80;
    const projection = d3.geoMercator()
        .center([10, 50])
        .scale(180)
        .translate([width / 2, height / 2]);

    const geoPath = d3.geoPath().projection(projection);

    const parseCoord = (c: string) => {
        const val = parseFloat(c);
        return (c.includes('S') || c.includes('W')) ? -val : val;
    };

    const stationsWithPos = STATIONS.map(s => {
        const [px, py] = projection([parseCoord(s.lng), parseCoord(s.lat)]) || [s.x, s.y];
        return { ...s, px, py };
    });

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Top Bar */}
            <div className="px-6 py-4 border-b border-[#1e1e24] flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                        <Radio className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                        <h2 className="text-sm font-bold text-white tracking-tight">DOMESTIC GROUND STATIONS</h2>
                        <p className="text-[10px] text-zinc-500 font-mono">Core Western Europe · {STATIONS.length} stations · 11 sensors · 5 actuators</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-mono text-emerald-400">
                        <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                        COVERAGE 97.3%
                    </div>
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 rounded text-[9px] font-mono text-blue-400">
                        AVG LATENCY {(12 + (Math.random() - 0.5) * 4).toFixed(0)}ms
                    </div>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Left: Map + Stations */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* SVG Map */}
                    <div className="flex-1 relative bg-[#060609] min-h-[280px]">
                        <svg viewBox="0 0 100 80" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
                            {/* Subtle grid */}
                            {Array.from({ length: 20 }, (_, i) => (
                                <line key={`vg${i}`} x1={i * 5} y1="0" x2={i * 5} y2="80" stroke="#1e1e24" strokeWidth="0.15" />
                            ))}
                            {Array.from({ length: 16 }, (_, i) => (
                                <line key={`hg${i}`} x1="0" y1={i * 5} x2="100" y2={i * 5} stroke="#1e1e24" strokeWidth="0.15" />
                            ))}

                            {/* Europe Map Background */}
                            {worldData && (
                                <g>
                                    {worldData.features.map((f: any, i: number) => (
                                        <path key={`c${i}`} d={geoPath(f) || ''} fill="#0a1929" stroke="#1a3a5c" strokeWidth="0.2" />
                                    ))}
                                </g>
                            )}

                            {/* Connection lines between adjacent stations */}
                            {[
                                [0, 3], [3, 4], [4, 1], [1, 5], [0, 1], [2, 3], [2, 7], [1, 6], [6, 2],
                            ].map(([a, b], i) => (
                                <line key={`link${i}`}
                                    x1={stationsWithPos[a].px} y1={stationsWithPos[a].py}
                                    x2={stationsWithPos[b].px} y2={stationsWithPos[b].py}
                                    stroke="#1a3a5c" strokeWidth="0.3" strokeDasharray="1,1"
                                    className="animate-flow" />
                            ))}

                            {/* Station nodes */}
                            {stationsWithPos.map(s => {
                                const isSelected = s.id === selected;
                                const color = s.status === 'WARNING' ? '#f59e0b' : s.status === 'CRITICAL' ? '#ef4444' : '#10b981';
                                return (
                                    <g key={s.id} onClick={() => setSelected(s.id)} className="cursor-pointer">
                                        {/* Pulse ring */}
                                        <circle cx={s.px} cy={s.py} r={isSelected ? 3 : 2} fill="none" stroke={color} strokeWidth="0.2" opacity={0.4}>
                                            <animate attributeName="r" from={isSelected ? '2' : '1.5'} to={isSelected ? '5' : '3.5'} dur="2s" repeatCount="indefinite" />
                                            <animate attributeName="opacity" from="0.6" to="0" dur="2s" repeatCount="indefinite" />
                                        </circle>
                                        {/* Core dot */}
                                        <circle cx={s.px} cy={s.py} r={isSelected ? 1.5 : 1} fill={color} />
                                        {/* Label */}
                                        <text x={s.px + 2} y={s.py + 0.5} fill={isSelected ? '#fff' : '#6b7280'} fontSize="2.2" fontFamily="monospace">{s.city}</text>
                                    </g>
                                );
                            })}
                        </svg>
                    </div>

                    {/* Station Table (scrollable) */}
                    <div className="h-[180px] border-t border-[#1e1e24] overflow-auto">
                        <table className="w-full text-[10px] font-mono">
                            <thead className="sticky top-0 bg-[#0a0a0c]">
                                <tr className="text-zinc-600 border-b border-[#1e1e24]">
                                    <th className="text-left px-4 py-2">STATION</th>
                                    <th className="text-left px-2 py-2">STATUS</th>
                                    <th className="text-right px-2 py-2">SIGNAL</th>
                                    <th className="text-right px-2 py-2">LATENCY</th>
                                    <th className="text-right px-2 py-2">VOLTAGE</th>
                                    <th className="text-right px-2 py-2">FREQ</th>
                                    <th className="text-right px-4 py-2">UPTIME</th>
                                </tr>
                            </thead>
                            <tbody>
                                {STATIONS.map(s => (
                                    <tr key={s.id}
                                        onClick={() => setSelected(s.id)}
                                        className={`border-b border-[#1e1e24]/50 cursor-pointer transition-colors ${s.id === selected ? 'bg-blue-500/5' : 'hover:bg-white/[0.02]'}`}>
                                        <td className="px-4 py-2 text-white font-medium">{s.name}</td>
                                        <td className="px-2 py-2">
                                            <span className={`px-1.5 py-0.5 rounded ${s.status === 'WARNING' ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-300'}`}>
                                                {s.status}
                                            </span>
                                        </td>
                                        <td className={`px-2 py-2 text-right ${s.signalDb < -50 ? 'text-amber-400' : 'text-zinc-300'}`}>
                                            {jitter(s.signalDb, 4).toFixed(0)} dBm
                                        </td>
                                        <td className={`px-2 py-2 text-right ${s.latencyMs > 20 ? 'text-amber-400' : 'text-zinc-300'}`}>
                                            {jitter(s.latencyMs, 3).toFixed(0)} ms
                                        </td>
                                        <td className="px-2 py-2 text-right text-zinc-300">{jitter(s.voltage, 0.01).toFixed(3)} pu</td>
                                        <td className="px-2 py-2 text-right text-zinc-300">{jitter(s.frequency, 0.03).toFixed(2)} Hz</td>
                                        <td className="px-4 py-2 text-right text-zinc-300">{s.uptimePct}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right: Selected Station Detail + Live Log */}
                <div className="w-[300px] border-l border-[#1e1e24] flex flex-col shrink-0">
                    {/* Selected Station Detail */}
                    <div className="p-4 border-b border-[#1e1e24]">
                        <div className="flex items-center gap-2 mb-3">
                            <MapPin className="w-3.5 h-3.5 text-blue-400" />
                            <span className="text-xs font-bold text-white">{selectedStation.name}</span>
                            <span className={`ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded ${selectedStation.status === 'WARNING' ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-300'}`}>
                                {selectedStation.status}
                            </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { label: 'Sensors', value: selectedStation.sensors },
                                { label: 'Actuators', value: selectedStation.actuators },
                                { label: 'Location', value: `${selectedStation.lat}` },
                                { label: 'Signal', value: `${selectedStation.signalDb} dBm` },
                            ].map(item => (
                                <div key={item.label} className="bg-[#0d0d12] border border-[#1e1e24] rounded p-2">
                                    <div className="text-[8px] font-mono text-zinc-600 uppercase">{item.label}</div>
                                    <div className="text-xs text-white font-mono mt-0.5">{item.value}</div>
                                </div>
                            ))}
                        </div>

                        {/* Signal Strength Bar */}
                        <div className="mt-3">
                            <div className="flex items-center justify-between text-[8px] font-mono text-zinc-600 mb-1">
                                <span>SIGNAL STRENGTH</span>
                                <span className="text-zinc-400">{selectedStation.signalDb} dBm</span>
                            </div>
                            <div className="w-full h-2 bg-[#0d0d12] rounded-full overflow-hidden">
                                <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{
                                        width: `${Math.max(0, 100 + selectedStation.signalDb)}%`,
                                        background: selectedStation.signalDb > -45 ? '#10b981' : selectedStation.signalDb > -55 ? '#f59e0b' : '#ef4444'
                                    }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Live Telemetry Feed */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <div className="px-4 py-2 border-b border-[#1e1e24] flex items-center gap-2">
                            <Activity className="w-3 h-3 text-emerald-500" />
                            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Live Telemetry Feed</span>
                        </div>
                        <div ref={logRef} className="flex-1 overflow-auto p-3 space-y-1">
                            {telemetryLog.map((msg, i) => (
                                <div key={i} className="text-[9px] font-mono text-zinc-500 leading-relaxed">
                                    <span className="text-zinc-600">{new Date().toLocaleTimeString('en-GB', { hour12: false })}</span>{' '}
                                    <span className={msg.includes('WARNING') || msg.includes('CRITICAL') ? 'text-amber-400' : 'text-zinc-400'}>{msg}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
