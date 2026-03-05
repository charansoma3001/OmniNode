"use client";

import { useEffect, useRef, useState } from "react";
import { useAgentLogs } from "@/hooks/useAgentLogs";

function TypewriterText({ text }: { text: string }) {
    const [displayed, setDisplayed] = useState("");

    useEffect(() => {
        let i = 0;
        setDisplayed("");

        // Fast typewriter effect (approx 10-20ms per char)
        const interval = setInterval(() => {
            if (i < text.length) {
                setDisplayed(prev => prev + text.charAt(i));
                i++;
            } else {
                clearInterval(interval);
            }
        }, 15);

        return () => clearInterval(interval);
    }, [text]);

    return <span>{displayed}</span>;
}

export function BrainScanner() {
    const { logs } = useAgentLogs();
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="flex-1 flex flex-col bg-black/40 backdrop-blur-md rounded-xl border border-blue-500/30 overflow-hidden shadow-[0_0_20px_rgba(59,130,246,0.15)] h-full relative">
            <div className="h-10 border-b border-blue-500/30 bg-blue-950/20 flex items-center px-4 flex-none z-10">
                <h2 className="text-xs font-semibold tracking-widest text-blue-400 uppercase flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee] animate-pulse" />
                    Brain Scanner [Strategic AI]
                </h2>
            </div>

            {/* Scanline overlay */}
            <div className="absolute inset-0 top-10 scanline-bg pointer-events-none" />

            <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto font-mono text-xs flex flex-col gap-3 z-10 relative">
                {logs.length === 0 ? (
                    <div className="text-cyan-600/50 typing-cursor uppercase tracking-widest">Awaiting neural uplink...</div>
                ) : (
                    logs.map((log, i) => {
                        const isError = log.level === 'error';
                        const isWarning = log.level === 'warning';
                        const isDecision = log.level === 'decision';

                        let textColorClass = 'text-cyan-300/80';
                        if (isError) textColorClass = 'text-red-500 font-bold glitch-text shadow-[0_0_10px_rgba(239,68,68,0.5)]';
                        if (isWarning) textColorClass = 'text-yellow-400 glitch-text';
                        if (isDecision) textColorClass = 'text-emerald-400 font-bold';

                        // Only apply typewriter to the very last message in the list
                        const isLatest = i === logs.length - 1;

                        return (
                            <div key={i} className={`flex items-start gap-3 ${textColorClass}`}>
                                <span className="text-cyan-700/50 text-[10px] mt-[3px] whitespace-nowrap">
                                    [{new Date(log.timestamp).toLocaleTimeString()}]
                                </span>
                                <div className="flex-1 leading-relaxed">
                                    {log.level === 'analyzing' && <span className="mr-2 opacity-80">▹</span>}
                                    {log.level === 'tool_call' && <span className="mr-2 text-purple-400 font-bold">»</span>}
                                    {log.level === 'decision' && <span className="mr-2 text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]">✓</span>}
                                    {isWarning && <span className="mr-2">⚠</span>}
                                    {isError && <span className="mr-2 animate-pulse">!</span>}

                                    {isLatest && !isError && !isWarning ? (
                                        <TypewriterText text={log.message} />
                                    ) : (
                                        <span>{log.message}</span>
                                    )}

                                    {isLatest && <span className="typing-cursor ml-1 inline-block w-1.5 h-3.5 bg-cyan-400 align-middle -mt-1 shadow-[0_0_5px_#22d3ee]" />}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
