"use client";

import { useEffect, useRef } from "react";
import { useAgentLogs } from "@/hooks/useAgentLogs";

export function BrainScanner() {
    const { logs } = useAgentLogs();
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="flex-1 flex flex-col bg-card rounded-xl border border-border/50 overflow-hidden shadow-lg h-full">
            <div className="h-10 border-b border-border/50 bg-muted/20 flex items-center px-4 flex-none">
                <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                    Brain Scanner [Strategic AI]
                </h2>
            </div>
            <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto font-mono text-sm flex flex-col gap-2">
                {logs.length === 0 ? (
                    <div className="text-muted-foreground typing-cursor">Awaiting neural uplink...</div>
                ) : (
                    logs.map((log, i) => (
                        <div key={i} className={`flex items-start gap-2 ${log.level === 'error' ? 'text-destructive' : log.level === 'warning' ? 'text-yellow-500' : 'text-primary/90'}`}>
                            <span className="text-muted-foreground/50 text-xs mt-0.5 whitespace-nowrap">
                                [{new Date(log.timestamp).toLocaleTimeString()}]
                            </span>
                            <div className="flex-1">
                                {log.level === 'analyzing' && <span className="mr-2">🧠</span>}
                                {log.level === 'tool_call' && <span className="mr-2 text-purple-400">🔧</span>}
                                {log.level === 'decision' && <span className="mr-2 text-emerald-400">✅</span>}
                                {log.level === 'warning' && <span className="mr-2">⚠️</span>}
                                <span className={log.level === 'decision' ? 'font-bold' : ''}>{log.message}</span>
                                {i === logs.length - 1 && <span className="typing-cursor ml-1 inline-block w-1.5 h-3.5 bg-primary/70 align-middle -mt-1" />}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
