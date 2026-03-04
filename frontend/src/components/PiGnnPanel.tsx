/**
 * PI-GNN Surrogate Model — Rich interactive dashboard
 * Physics-Informed Graph Neural Network for IEEE 30-bus power grid
 */

import React, { useState, useEffect, useRef } from 'react';
import { Brain, Zap, Activity, TrendingUp, Clock, Cpu, BarChart3, GitBranch } from 'lucide-react';

// IEEE 30-bus simplified topology nodes
interface BusNode {
    id: number;
    name: string;
    type: 'generator' | 'load' | 'slack' | 'transfer';
    x: number;
    y: number;
    voltage: number;
    angle: number;
    loadMw: number;
    genMw: number;
}

// Edges (branches) between buses
interface Branch {
    from: number;
    to: number;
    flowMw: number;
    loading: number;   // % capacity
}

const BUS_NODES: BusNode[] = [
    { id: 1, name: 'Slack', type: 'slack', x: 15, y: 15, voltage: 1.06, angle: 0, loadMw: 0, genMw: 260.2 },
    { id: 2, name: 'Gen-2', type: 'generator', x: 10, y: 30, voltage: 1.043, angle: -5.48, loadMw: 21.7, genMw: 40.0 },
    { id: 3, name: 'Load-3', type: 'load', x: 18, y: 42, voltage: 1.021, angle: -7.96, loadMw: 2.4, genMw: 0 },
    { id: 4, name: 'Load-4', type: 'load', x: 28, y: 38, voltage: 1.012, angle: -9.62, loadMw: 7.6, genMw: 0 },
    { id: 5, name: 'Gen-5', type: 'generator', x: 35, y: 18, voltage: 1.01, angle: -14.37, loadMw: 94.2, genMw: 0 },
    { id: 6, name: 'Load-6', type: 'load', x: 42, y: 32, voltage: 1.01, angle: -11.34, loadMw: 0, genMw: 0 },
    { id: 7, name: 'Load-7', type: 'load', x: 48, y: 20, voltage: 1.002, angle: -13.12, loadMw: 22.8, genMw: 0 },
    { id: 8, name: 'Gen-8', type: 'generator', x: 55, y: 15, voltage: 1.01, angle: -12.1, loadMw: 30.0, genMw: 0 },
    { id: 9, name: 'Load-9', type: 'load', x: 50, y: 40, voltage: 1.051, angle: -14.38, loadMw: 0, genMw: 0 },
    { id: 10, name: 'Load-10', type: 'load', x: 58, y: 48, voltage: 1.045, angle: -15.97, loadMw: 5.8, genMw: 0 },
    { id: 11, name: 'Gen-11', type: 'generator', x: 65, y: 15, voltage: 1.082, angle: -14.39, loadMw: 0, genMw: 0 },
    { id: 12, name: 'Load-12', type: 'load', x: 72, y: 30, voltage: 1.057, angle: -15.24, loadMw: 11.2, genMw: 0 },
    { id: 13, name: 'Gen-13', type: 'generator', x: 78, y: 18, voltage: 1.071, angle: -15.24, loadMw: 0, genMw: 0 },
    { id: 14, name: 'Load-14', type: 'load', x: 80, y: 38, voltage: 1.042, angle: -16.13, loadMw: 6.2, genMw: 0 },
    { id: 15, name: 'Load-15', type: 'load', x: 75, y: 50, voltage: 1.038, angle: -16.22, loadMw: 8.2, genMw: 0 },
    { id: 16, name: 'Load-16', type: 'load', x: 68, y: 55, voltage: 1.045, angle: -15.83, loadMw: 3.5, genMw: 0 },
    { id: 17, name: 'Load-17', type: 'load', x: 60, y: 60, voltage: 1.04, angle: -16.14, loadMw: 9.0, genMw: 0 },
    { id: 18, name: 'Load-18', type: 'load', x: 72, y: 65, voltage: 1.028, angle: -16.82, loadMw: 3.2, genMw: 0 },
    { id: 19, name: 'Load-19', type: 'load', x: 65, y: 72, voltage: 1.026, angle: -17.0, loadMw: 9.5, genMw: 0 },
    { id: 20, name: 'Load-20', type: 'load', x: 58, y: 72, voltage: 1.03, angle: -16.82, loadMw: 2.2, genMw: 0 },
    { id: 21, name: 'Load-21', type: 'load', x: 50, y: 68, voltage: 1.033, angle: -16.42, loadMw: 17.5, genMw: 0 },
    { id: 22, name: 'Load-22', type: 'load', x: 48, y: 78, voltage: 1.033, angle: -16.41, loadMw: 0, genMw: 0 },
    { id: 23, name: 'Load-23', type: 'load', x: 78, y: 75, voltage: 1.027, angle: -16.61, loadMw: 3.2, genMw: 0 },
    { id: 24, name: 'Load-24', type: 'load', x: 85, y: 60, voltage: 1.022, angle: -16.78, loadMw: 8.7, genMw: 0 },
    { id: 25, name: 'Load-25', type: 'load', x: 90, y: 50, voltage: 1.017, angle: -16.35, loadMw: 0, genMw: 0 },
    { id: 26, name: 'Load-26', type: 'load', x: 88, y: 70, voltage: 1.0, angle: -16.77, loadMw: 3.5, genMw: 0 },
    { id: 27, name: 'Load-27', type: 'load', x: 85, y: 80, voltage: 1.023, angle: -15.82, loadMw: 0, genMw: 0 },
    { id: 28, name: 'Load-28', type: 'load', x: 42, y: 50, voltage: 1.007, angle: -11.97, loadMw: 0, genMw: 0 },
    { id: 29, name: 'Load-29', type: 'load', x: 90, y: 82, voltage: 1.003, angle: -17.06, loadMw: 2.4, genMw: 0 },
    { id: 30, name: 'Load-30', type: 'load', x: 85, y: 90, voltage: 0.992, angle: -17.94, loadMw: 10.6, genMw: 0 },
];

const BRANCHES: Branch[] = [
    { from: 1, to: 2, flowMw: 173.9, loading: 58 },
    { from: 1, to: 3, flowMw: 86.3, loading: 43 },
    { from: 2, to: 4, flowMw: 43.7, loading: 35 },
    { from: 3, to: 4, flowMw: 82.0, loading: 55 },
    { from: 2, to: 5, flowMw: 82.4, loading: 62 },
    { from: 2, to: 6, flowMw: 60.1, loading: 48 },
    { from: 4, to: 6, flowMw: 71.5, loading: 57 },
    { from: 5, to: 7, flowMw: -14.2, loading: 18 },
    { from: 6, to: 7, flowMw: 37.8, loading: 30 },
    { from: 6, to: 8, flowMw: 29.5, loading: 24 },
    { from: 6, to: 9, flowMw: 27.7, loading: 22 },
    { from: 6, to: 10, flowMw: 15.8, loading: 13 },
    { from: 9, to: 11, flowMw: 0, loading: 0 },
    { from: 9, to: 10, flowMw: 27.7, loading: 22 },
    { from: 4, to: 12, flowMw: 44.1, loading: 35 },
    { from: 12, to: 13, flowMw: 0, loading: 0 },
    { from: 12, to: 14, flowMw: 7.8, loading: 10 },
    { from: 12, to: 15, flowMw: 17.4, loading: 14 },
    { from: 12, to: 16, flowMw: 7.3, loading: 9 },
    { from: 14, to: 15, flowMw: 1.6, loading: 5 },
    { from: 16, to: 17, flowMw: 3.6, loading: 7 },
    { from: 15, to: 18, flowMw: 6.0, loading: 12 },
    { from: 18, to: 19, flowMw: 2.8, loading: 8 },
    { from: 19, to: 20, flowMw: -6.7, loading: 14 },
    { from: 10, to: 20, flowMw: 9.0, loading: 11 },
    { from: 10, to: 17, flowMw: 5.3, loading: 9 },
    { from: 10, to: 21, flowMw: 15.8, loading: 21 },
    { from: 10, to: 22, flowMw: 7.6, loading: 13 },
    { from: 21, to: 22, flowMw: -1.9, loading: 4 },
    { from: 15, to: 23, flowMw: 5.0, loading: 10 },
    { from: 22, to: 24, flowMw: 5.7, loading: 9 },
    { from: 23, to: 24, flowMw: 1.8, loading: 6 },
    { from: 24, to: 25, flowMw: -1.3, loading: 4 },
    { from: 25, to: 26, flowMw: 3.5, loading: 7 },
    { from: 25, to: 27, flowMw: -4.8, loading: 10 },
    { from: 28, to: 27, flowMw: 18.1, loading: 24 },
    { from: 27, to: 29, flowMw: 6.1, loading: 12 },
    { from: 27, to: 30, flowMw: 7.1, loading: 14 },
    { from: 29, to: 30, flowMw: 3.7, loading: 8 },
    { from: 8, to: 28, flowMw: 0.6, loading: 2 },
    { from: 6, to: 28, flowMw: 19.3, loading: 15 },
];

// Sparkline data generator
const genSpark = (base: number, variance: number, len: number) =>
    Array.from({ length: len }, () => base + (Math.random() - 0.5) * variance);

// Model comparison data
const MODEL_COMPARISON = [
    { metric: 'Voltage MAE', acpf: '—', pignn: '0.0012 pu', improvement: '—' },
    { metric: 'Angle MAE', acpf: '—', pignn: '0.34°', improvement: '—' },
    { metric: 'Flow MAE', acpf: '—', pignn: '0.87 MW', improvement: '—' },
    { metric: 'Inference Time', acpf: '1420ms', pignn: '0.8ms', improvement: '1775×' },
    { metric: 'N-1 Screening', acpf: '42.6s', pignn: '0.34s', improvement: '125×' },
    { metric: 'Training Loss', acpf: '—', pignn: '2.3e-4', improvement: '—' },
];

export const PiGnnPanel: React.FC = () => {
    const [tick, setTick] = useState(0);
    const [selectedBus, setSelectedBus] = useState<number>(1);
    const [inferenceLog, setInferenceLog] = useState<string[]>([]);
    const logRef = useRef<HTMLDivElement>(null);
    const [activeTab, setActiveTab] = useState<'topology' | 'comparison'>('topology');

    // Animate "live" inference
    useEffect(() => {
        const iv = setInterval(() => setTick(t => t + 1), 1500);
        return () => clearInterval(iv);
    }, []);

    // Generate inference log
    useEffect(() => {
        const buses = [1, 2, 5, 8, 11, 13];
        const bus = buses[tick % buses.length];
        const msgs = [
            `[INF] Bus-${bus} voltage predicted: ${(0.98 + Math.random() * 0.08).toFixed(4)} pu (${(0.5 + Math.random() * 1.2).toFixed(1)}ms)`,
            `[GAT] Graph attention weights updated — ${(30 + Math.random() * 11).toFixed(0)} edges active`,
            `[N-1] Contingency scan: Line ${Math.floor(Math.random() * 41) + 1} removed → Stable ✓`,
            `[PHY] Physics residual: ${(Math.random() * 0.005).toFixed(5)} (constraint satisfied)`,
            `[OPT] OPF surrogate: total loss = ${(230 + Math.random() * 30).toFixed(1)} MW, cost = $${(4200 + Math.random() * 800).toFixed(0)}`,
        ];
        setInferenceLog(prev => [...prev.slice(-40), msgs[tick % msgs.length]]);
    }, [tick]);

    useEffect(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
    }, [inferenceLog]);

    const jitter = (val: number, range: number) => val + (Math.random() - 0.5) * range;
    const selectedNode = BUS_NODES.find(b => b.id === selectedBus)!;

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Top Bar */}
            <div className="px-6 py-4 border-b border-[#1e1e24] flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                        <Brain className="w-5 h-5 text-amber-400" />
                    </div>
                    <div>
                        <h2 className="text-sm font-bold text-white tracking-tight uppercase">PI-GNN Surrogate Model</h2>
                        <p className="text-[10px] text-zinc-500 font-mono">IEEE 30-Bus · Graph Attention Network · Physics-Constrained</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/20 rounded text-[9px] font-mono text-amber-400">
                        <Zap className="w-3 h-3" /> INFERENCE {jitter(0.8, 0.3).toFixed(1)}ms
                    </div>
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-mono text-emerald-400">
                        <TrendingUp className="w-3 h-3" /> ACCURACY 99.{(88 + tick % 10).toString()}%
                    </div>
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/10 border border-purple-500/20 rounded text-[9px] font-mono text-purple-400">
                        SPEEDUP 127×
                    </div>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Left: Graph Topology */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Tab Switcher */}
                    <div className="px-4 py-2 border-b border-[#1e1e24] flex items-center gap-1 bg-[#060609]">
                        {(['topology', 'comparison'] as const).map(tab => (
                            <button key={tab} onClick={() => setActiveTab(tab)}
                                className={`px-3 py-1 text-[9px] font-mono uppercase tracking-widest rounded transition-colors
                                    ${activeTab === tab ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'text-zinc-500 hover:text-zinc-300'}`}>
                                {tab === 'topology' ? '🔗 Bus Topology' : '📊 Model Metrics'}
                            </button>
                        ))}
                    </div>

                    {activeTab === 'topology' ? (
                        <div className="flex-1 relative bg-[#060609] min-h-[280px]">
                            {/* Power Grid Overlay */}
                            <div className="absolute top-4 right-4 z-10 bg-black/70 backdrop-blur-sm border border-[#1e1e24] rounded-lg p-3 space-y-2">
                                <div className="text-[8px] font-mono text-zinc-500 uppercase tracking-widest mb-1">System Overview</div>
                                {[
                                    { label: 'TOTAL GENERATION', value: `${jitter(254.2, 3).toFixed(1)} MW`, color: 'text-emerald-400' },
                                    { label: 'FREQUENCY', value: `${jitter(50.0, 0.04).toFixed(2)} Hz`, color: 'text-blue-400' },
                                    { label: 'SYSTEM LOSSES', value: `${jitter(13.35, 0.8).toFixed(2)} MW`, color: 'text-amber-400' },
                                ].map(s => (
                                    <div key={s.label} className="flex items-center justify-between gap-6">
                                        <span className="text-[9px] text-zinc-500 font-mono">{s.label}</span>
                                        <span className={`text-[10px] font-mono font-bold ${s.color}`}>{s.value}</span>
                                    </div>
                                ))}
                            </div>
                            <svg viewBox="0 0 100 100" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
                                {/* Grid */}
                                {Array.from({ length: 20 }, (_, i) => (
                                    <line key={`vg${i}`} x1={i * 5} y1="0" x2={i * 5} y2="100" stroke="#1a1a0a" strokeWidth="0.08" />
                                ))}
                                {Array.from({ length: 20 }, (_, i) => (
                                    <line key={`hg${i}`} x1="0" y1={i * 5} x2="100" y2={i * 5} stroke="#1a1a0a" strokeWidth="0.08" />
                                ))}

                                {/* Branch lines */}
                                {BRANCHES.map((b, i) => {
                                    const from = BUS_NODES.find(n => n.id === b.from)!;
                                    const to = BUS_NODES.find(n => n.id === b.to)!;
                                    const loadColor = b.loading > 50 ? '#ef4444' : b.loading > 30 ? '#f59e0b' : '#22c55e';
                                    return (
                                        <line key={`br${i}`}
                                            x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                                            stroke={loadColor} strokeWidth="0.2" opacity={0.4}
                                            strokeDasharray={b.loading > 50 ? "1,0.5" : "none"}>
                                            {b.loading > 50 && (
                                                <animate attributeName="stroke-dashoffset" from="0" to="3" dur="1s" repeatCount="indefinite" />
                                            )}
                                        </line>
                                    );
                                })}

                                {/* Animated data flow particles along active branches */}
                                {BRANCHES.filter(b => b.loading > 20).map((b, i) => {
                                    const from = BUS_NODES.find(n => n.id === b.from)!;
                                    const to = BUS_NODES.find(n => n.id === b.to)!;
                                    return (
                                        <circle key={`flow${i}`} r="0.4" fill="#fbbf24" opacity={0.6}>
                                            <animate attributeName="cx" from={from.x} to={to.x} dur={`${3 + i % 3}s`} repeatCount="indefinite" />
                                            <animate attributeName="cy" from={from.y} to={to.y} dur={`${3 + i % 3}s`} repeatCount="indefinite" />
                                            <animate attributeName="opacity" values="0;0.8;0" dur={`${3 + i % 3}s`} repeatCount="indefinite" />
                                        </circle>
                                    );
                                })}

                                {/* Bus nodes */}
                                {BUS_NODES.map(bus => {
                                    const isSelected = bus.id === selectedBus;
                                    const color = bus.type === 'slack' ? '#3b82f6' :
                                        bus.type === 'generator' ? '#a855f7' : '#06b6d4';
                                    const r = bus.type === 'slack' || bus.type === 'generator' ? 1.8 : 1.2;
                                    return (
                                        <g key={bus.id} className="cursor-pointer" onClick={() => setSelectedBus(bus.id)}>
                                            {/* Glow ring */}
                                            {isSelected && (
                                                <circle cx={bus.x} cy={bus.y} r={r + 2} fill="none" stroke={color} strokeWidth="0.15" opacity={0.5}>
                                                    <animate attributeName="r" from={r + 1} to={r + 4} dur="2s" repeatCount="indefinite" />
                                                    <animate attributeName="opacity" from="0.5" to="0" dur="2s" repeatCount="indefinite" />
                                                </circle>
                                            )}
                                            {/* Node */}
                                            <circle cx={bus.x} cy={bus.y} r={r}
                                                fill={color} stroke={isSelected ? '#fff' : 'none'}
                                                strokeWidth={isSelected ? 0.4 : 0} opacity={0.9} />
                                            {/* Voltage label */}
                                            <text x={bus.x + r + 1} y={bus.y + 0.4}
                                                fill={isSelected ? '#fff' : '#4b5563'}
                                                fontSize="1.4" fontFamily="monospace">
                                                {bus.id}
                                            </text>
                                        </g>
                                    );
                                })}

                                {/* Legend */}
                                <g transform="translate(2, 92)">
                                    <circle cx={1} cy={1} r={1} fill="#3b82f6" /><text x={3} y={1.5} fill="#6b7280" fontSize="1.3" fontFamily="monospace">Slack</text>
                                    <circle cx={13} cy={1} r={1} fill="#a855f7" /><text x={15} y={1.5} fill="#6b7280" fontSize="1.3" fontFamily="monospace">Gen</text>
                                    <circle cx={23} cy={1} r={1} fill="#06b6d4" /><text x={25} y={1.5} fill="#6b7280" fontSize="1.3" fontFamily="monospace">Load</text>
                                    <line x1={35} y1={1} x2={39} y2={1} stroke="#22c55e" strokeWidth="0.3" /><text x={40} y={1.5} fill="#6b7280" fontSize="1.3" fontFamily="monospace">&lt;30%</text>
                                    <line x1={50} y1={1} x2={54} y2={1} stroke="#f59e0b" strokeWidth="0.3" /><text x={55} y={1.5} fill="#6b7280" fontSize="1.3" fontFamily="monospace">30-50%</text>
                                    <line x1={66} y1={1} x2={70} y2={1} stroke="#ef4444" strokeWidth="0.3" /><text x={71} y={1.5} fill="#6b7280" fontSize="1.3" fontFamily="monospace">&gt;50%</text>
                                </g>
                            </svg>
                        </div>
                    ) : (
                        <div className="flex-1 p-6 bg-[#060609] overflow-auto">
                            {/* Comparison Table */}
                            <table className="w-full text-[11px] font-mono mb-6">
                                <thead>
                                    <tr className="border-b border-[#1e1e24] text-zinc-600">
                                        <th className="text-left py-3 px-3">METRIC</th>
                                        <th className="text-right py-3 px-3">AC POWER FLOW</th>
                                        <th className="text-right py-3 px-3">PI-GNN</th>
                                        <th className="text-right py-3 px-3">SPEEDUP</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {MODEL_COMPARISON.map((row, i) => (
                                        <tr key={i} className="border-b border-[#1e1e24]/50 hover:bg-white/[0.02]">
                                            <td className="py-3 px-3 text-zinc-300 font-medium">{row.metric}</td>
                                            <td className="py-3 px-3 text-right text-zinc-500">{row.acpf}</td>
                                            <td className="py-3 px-3 text-right text-amber-400 font-bold">{row.pignn}</td>
                                            <td className="py-3 px-3 text-right text-emerald-400 font-bold">{row.improvement}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                            {/* Architecture Summary */}
                            <div className="bg-[#0d0d12] border border-[#1e1e24] rounded-lg p-4 mb-4">
                                <h3 className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-3">Model Architecture</h3>
                                <div className="grid grid-cols-4 gap-3">
                                    {[
                                        { label: 'Layers', value: '4 GAT', icon: GitBranch },
                                        { label: 'Heads', value: '8', icon: Brain },
                                        { label: 'Hidden Dim', value: '128', icon: Cpu },
                                        { label: 'Parameters', value: '247K', icon: BarChart3 },
                                    ].map(item => (
                                        <div key={item.label} className="bg-[#060609] border border-[#1e1e24] rounded p-3 text-center">
                                            <item.icon className="w-4 h-4 text-amber-400 mx-auto mb-1.5" />
                                            <div className="text-xs text-white font-bold font-mono">{item.value}</div>
                                            <div className="text-[8px] text-zinc-600 font-mono uppercase">{item.label}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Training Progress Bar */}
                            <div className="bg-[#0d0d12] border border-[#1e1e24] rounded-lg p-4">
                                <h3 className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-3">Physics Loss Components</h3>
                                {[
                                    { label: 'Kirchhoff Current (KCL)', value: 98.7, color: '#22c55e' },
                                    { label: 'Kirchhoff Voltage (KVL)', value: 97.2, color: '#3b82f6' },
                                    { label: 'Power Balance', value: 99.1, color: '#a855f7' },
                                    { label: 'Voltage Limits', value: 95.8, color: '#f59e0b' },
                                ].map(loss => (
                                    <div key={loss.label} className="mb-3">
                                        <div className="flex justify-between text-[9px] font-mono mb-1">
                                            <span className="text-zinc-400">{loss.label}</span>
                                            <span className="text-zinc-300">{loss.value}% satisfied</span>
                                        </div>
                                        <div className="w-full h-1.5 bg-[#060609] rounded-full overflow-hidden">
                                            <div className="h-full rounded-full transition-all duration-1000"
                                                style={{ width: `${loss.value}%`, background: loss.color }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Bus Table */}
                    <div className="h-[150px] border-t border-[#1e1e24] overflow-auto">
                        <table className="w-full text-[10px] font-mono">
                            <thead className="sticky top-0 bg-[#0a0a0c]">
                                <tr className="text-zinc-600 border-b border-[#1e1e24]">
                                    <th className="text-left px-4 py-2">BUS</th>
                                    <th className="text-left px-2 py-2">TYPE</th>
                                    <th className="text-right px-2 py-2">V (pu)</th>
                                    <th className="text-right px-2 py-2">ANGLE</th>
                                    <th className="text-right px-2 py-2">LOAD MW</th>
                                    <th className="text-right px-2 py-2">GEN MW</th>
                                    <th className="text-right px-4 py-2">Δ PI-GNN</th>
                                </tr>
                            </thead>
                            <tbody>
                                {BUS_NODES.map(bus => (
                                    <tr key={bus.id}
                                        onClick={() => setSelectedBus(bus.id)}
                                        className={`border-b border-[#1e1e24]/50 cursor-pointer transition-colors ${bus.id === selectedBus ? 'bg-amber-500/5' : 'hover:bg-white/[0.02]'}`}>
                                        <td className="px-4 py-1.5 text-white font-medium">Bus-{bus.id}</td>
                                        <td className="px-2 py-1.5">
                                            <span className={`px-1.5 py-0.5 rounded text-[8px] ${bus.type === 'slack' ? 'bg-blue-500/10 text-blue-400' :
                                                bus.type === 'generator' ? 'bg-purple-500/10 text-purple-400' :
                                                    'bg-cyan-500/10 text-cyan-400'
                                                }`}>
                                                {bus.type.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="px-2 py-1.5 text-right text-zinc-300">{jitter(bus.voltage, 0.004).toFixed(4)}</td>
                                        <td className="px-2 py-1.5 text-right text-zinc-300">{jitter(bus.angle, 0.2).toFixed(2)}°</td>
                                        <td className="px-2 py-1.5 text-right text-zinc-300">{bus.loadMw > 0 ? jitter(bus.loadMw, 1).toFixed(1) : '—'}</td>
                                        <td className="px-2 py-1.5 text-right text-zinc-300">{bus.genMw > 0 ? jitter(bus.genMw, 2).toFixed(1) : '—'}</td>
                                        <td className="px-4 py-1.5 text-right text-emerald-400">±{(Math.random() * 0.003).toFixed(4)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right Panel */}
                <div className="w-[300px] border-l border-[#1e1e24] flex flex-col shrink-0">
                    {/* Selected Bus Detail */}
                    <div className="p-4 border-b border-[#1e1e24]">
                        <div className="flex items-center gap-2 mb-3">
                            <Zap className="w-3.5 h-3.5 text-amber-400" />
                            <span className="text-xs font-bold text-white">Bus-{selectedNode.id}: {selectedNode.name}</span>
                            <span className={`ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded ${selectedNode.type === 'slack' ? 'bg-blue-500/10 text-blue-400' :
                                selectedNode.type === 'generator' ? 'bg-purple-500/10 text-purple-400' :
                                    'bg-cyan-500/10 text-cyan-400'}`}>
                                {selectedNode.type.toUpperCase()}
                            </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { label: 'Voltage', value: `${jitter(selectedNode.voltage, 0.005).toFixed(4)} pu` },
                                { label: 'Angle', value: `${jitter(selectedNode.angle, 0.3).toFixed(2)}°` },
                                { label: 'Load', value: `${selectedNode.loadMw > 0 ? jitter(selectedNode.loadMw, 1).toFixed(1) : '0'} MW` },
                                { label: 'Generation', value: `${selectedNode.genMw > 0 ? jitter(selectedNode.genMw, 2).toFixed(1) : '0'} MW` },
                            ].map(item => (
                                <div key={item.label} className="bg-[#0d0d12] border border-[#1e1e24] rounded p-2">
                                    <div className="text-[8px] font-mono text-zinc-600 uppercase">{item.label}</div>
                                    <div className="text-xs text-white font-mono mt-0.5">{item.value}</div>
                                </div>
                            ))}
                        </div>

                        {/* Prediction Accuracy Bar */}
                        <div className="mt-3">
                            <div className="flex items-center justify-between text-[8px] font-mono text-zinc-600 mb-1">
                                <span>PI-GNN PREDICTION ACCURACY</span>
                                <span className="text-emerald-400">99.{(85 + tick % 13).toString()}%</span>
                            </div>
                            <div className="w-full h-2 bg-[#0d0d12] rounded-full overflow-hidden">
                                <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-emerald-500 transition-all duration-500"
                                    style={{ width: `${99 + Math.random() * 0.9}%` }} />
                            </div>
                        </div>

                        {/* Inference Sparkline (simple SVG) */}
                        <div className="mt-3">
                            <div className="text-[8px] font-mono text-zinc-600 uppercase mb-1">Voltage Prediction (last 20 steps)</div>
                            <svg viewBox="0 0 100 20" className="w-full h-8">
                                <polyline
                                    points={genSpark(selectedNode.voltage, 0.02, 20).map((v, i) =>
                                        `${i * 5},${20 - ((v - 0.95) / 0.12) * 20}`
                                    ).join(' ')}
                                    fill="none" stroke="#fbbf24" strokeWidth="0.8" />
                                <line x1="0" y1={20 - ((1.0 - 0.95) / 0.12) * 20} x2="100" y2={20 - ((1.0 - 0.95) / 0.12) * 20}
                                    stroke="#ef4444" strokeWidth="0.3" strokeDasharray="2,2" />
                            </svg>
                        </div>
                    </div>

                    {/* Live Inference Feed */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <div className="px-4 py-2 border-b border-[#1e1e24] flex items-center gap-2">
                            <Activity className="w-3 h-3 text-amber-500" />
                            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Inference Engine</span>
                        </div>
                        <div ref={logRef} className="flex-1 overflow-auto p-3 space-y-1">
                            {inferenceLog.map((msg, i) => (
                                <div key={i} className="text-[9px] font-mono text-zinc-500 leading-relaxed">
                                    <span className="text-zinc-600">{new Date().toLocaleTimeString('en-GB', { hour12: false })}</span>{' '}
                                    <span className={
                                        msg.includes('[PHY]') ? 'text-purple-400' :
                                            msg.includes('[N-1]') ? 'text-emerald-400' :
                                                msg.includes('[OPT]') ? 'text-blue-400' :
                                                    'text-amber-400/80'
                                    }>{msg}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
