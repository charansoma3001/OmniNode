"use client";

import { Card } from "@/components/ui/card";
import { useGridState } from "@/hooks/useGridState";
import CountUp from 'react-countup';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import { useMemo, useEffect, useState } from 'react';

// Keep a small rolling history for sparklines
const MAX_HISTORY = 40;

export function KpiCards() {
    const { gridData } = useGridState();

    const [history, setHistory] = useState<{ gen: number, load: number }[]>([]);

    useEffect(() => {
        if (gridData) {
            setHistory(prev => {
                const next = [...prev, { gen: gridData.total_generation_mw, load: gridData.total_load_mw }];
                if (next.length > MAX_HISTORY) return next.slice(next.length - MAX_HISTORY);
                return next;
            });
        }
    }, [gridData]);

    if (!gridData) {
        return (
            <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(i => (
                    <Card key={i} className="p-4 bg-black/40 border-blue-500/20 backdrop-blur-md animate-pulse h-20 shadow-[0_0_15px_rgba(59,130,246,0.1)]" />
                ))}
            </div>
        );
    }

    // Count active violations
    const violationCount = gridData.violations.length;
    const isHealthy = violationCount === 0;

    return (
        <div className="grid grid-cols-4 gap-4">
            <Card className="p-4 bg-black/40 border-blue-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(59,130,246,0.15)] relative overflow-hidden group">
                <div className="relative z-10">
                    <div className="text-xs text-blue-400/80 uppercase tracking-widest font-semibold mb-1">Total Generation</div>
                    <div className="text-3xl font-bold font-mono text-blue-100 flex items-baseline gap-1">
                        <CountUp end={gridData.total_generation_mw} decimals={1} duration={1} preserveValue />
                        <span className="text-sm border-blue-500/50 text-blue-400">MW</span>
                    </div>
                </div>
                {/* Sparkline Background */}
                <div className="absolute inset-0 top-6 opacity-20 group-hover:opacity-40 transition-opacity pointer-events-none">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={history}>
                            <YAxis domain={['dataMin - 10', 'dataMax + 10']} hide />
                            <Line type="monotone" dataKey="gen" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </Card>

            <Card className="p-4 bg-black/40 border-cyan-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(34,211,238,0.15)] relative overflow-hidden group">
                <div className="relative z-10">
                    <div className="text-xs text-cyan-400/80 uppercase tracking-widest font-semibold mb-1">Total Load</div>
                    <div className="text-3xl font-bold font-mono text-cyan-100 flex items-baseline gap-1">
                        <CountUp end={gridData.total_load_mw} decimals={1} duration={1} preserveValue />
                        <span className="text-sm text-cyan-400">MW</span>
                    </div>
                </div>
                {/* Sparkline Background */}
                <div className="absolute inset-0 top-6 opacity-20 group-hover:opacity-40 transition-opacity pointer-events-none">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={history}>
                            <YAxis domain={['dataMin - 10', 'dataMax + 10']} hide />
                            <Line type="monotone" dataKey="load" stroke="#22d3ee" strokeWidth={2} dot={false} isAnimationActive={false} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </Card>

            <Card className="p-4 bg-black/40 border-emerald-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(16,185,129,0.15)] flex flex-col justify-center">
                <div className="text-xs text-emerald-400/80 uppercase tracking-widest font-semibold mb-1">Grid Frequency</div>
                <div className="text-3xl font-bold font-mono text-emerald-100 flex items-baseline gap-1">
                    <CountUp end={gridData.frequency_hz} decimals={2} duration={1} preserveValue />
                    <span className="text-sm text-emerald-400">Hz</span>
                </div>
            </Card>

            <Card className={`p-4 bg-black/40 backdrop-blur-md flex flex-col justify-center border transition-colors duration-500 ${isHealthy ? 'border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]' : 'border-red-500/50 shadow-[0_0_25px_rgba(239,68,68,0.4)]'}`}>
                <div className={`text-xs uppercase tracking-widest font-semibold mb-1 ${isHealthy ? 'text-emerald-400/80' : 'text-red-400/90'}`}>System Status</div>
                <div className={`text-2xl font-bold tracking-wide uppercase ${isHealthy ? 'text-emerald-400' : 'text-red-500 glitch-text'}`}>
                    {isHealthy ? 'Optimal' : `${violationCount} Violations`}
                </div>
            </Card>
        </div>
    );
}
