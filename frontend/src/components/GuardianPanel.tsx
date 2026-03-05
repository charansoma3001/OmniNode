"use client";

import { useGuardianEvents } from "@/hooks/useGuardianEvents";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, ShieldCheck, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

// Simulates a tiny delay before stamping "APPROVED" to show the spinner
function ActionStamp({ safe }: { safe: boolean }) {
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => setLoading(false), 400); // 400ms fake delay
        return () => clearTimeout(timer);
    }, []);

    if (loading) {
        return (
            <div className="flex items-center gap-2 text-cyan-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="font-mono text-xs animate-pulse tracking-widest uppercase">Analyzing...</span>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2">
            {safe ? (
                <ShieldCheck className="h-4 w-4 text-emerald-400 drop-shadow-[0_0_5px_rgba(16,185,129,0.8)]" />
            ) : (
                <ShieldAlert className="h-4 w-4 text-red-500 drop-shadow-[0_0_5px_rgba(239,68,68,0.8)] animate-pulse" />
            )}
            <span className={`font-mono text-xs font-bold tracking-widest uppercase ${safe ? 'text-emerald-400' : 'text-red-500'}`}>
                {safe ? "APPROVED" : "BLOCKED"}
            </span>
        </div>
    );
}

export function GuardianPanel() {
    const { events } = useGuardianEvents();

    return (
        <div className="flex-1 flex flex-col bg-black/40 backdrop-blur-md rounded-xl border border-emerald-500/30 overflow-hidden shadow-[0_0_20px_rgba(16,185,129,0.1)] h-full">
            <div className="h-10 border-b border-emerald-500/30 bg-emerald-950/20 flex items-center px-4 flex-none gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse" />
                <h2 className="text-xs font-semibold tracking-widest text-emerald-500 uppercase">
                    Guardian Intercept
                </h2>
            </div>

            <div className="flex-1 p-4 overflow-y-auto w-full">
                <div className="flex flex-col gap-3">
                    {events.length === 0 ? (
                        <div className="text-xs text-emerald-700/50 uppercase tracking-widest p-4 text-center typing-cursor">
                            Monitoring command stream...
                        </div>
                    ) : (
                        <AnimatePresence>
                            {events.map((evt, idx) => (
                                <motion.div
                                    key={`${evt.timestamp}-${idx}`}
                                    // Slide in aggressively from the left
                                    initial={{ opacity: 0, x: -50, scale: 0.95 }}
                                    animate={{ opacity: 1, x: 0, scale: 1 }}
                                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                    className="overflow-hidden"
                                >
                                    <div className={`p-3 rounded-lg backdrop-blur-md text-sm transition-all duration-300 border ${evt.safe
                                        ? 'bg-emerald-950/20 border-emerald-500/50 hover:border-emerald-400 shadow-[inset_0_0_10px_rgba(16,185,129,0.1)]'
                                        : 'bg-red-950/20 border-red-500/50 hover:border-red-400 shadow-[inset_0_0_15px_rgba(239,68,68,0.2)]'
                                        }`}>
                                        <div className="flex items-start justify-between mb-3">
                                            <ActionStamp safe={evt.safe} />
                                            <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold tracking-widest ${evt.safe ? 'border border-emerald-500/50 text-emerald-400' : 'bg-red-500 text-white shadow-[0_0_10px_rgba(239,68,68,0.6)]'}`}>
                                                {evt.risk_level} risk
                                            </span>
                                        </div>

                                        <div className="font-mono text-xs mb-3 p-2 bg-black/60 rounded border border-white/5 flex flex-wrap items-center gap-1.5">
                                            <span className="text-cyan-400 font-semibold">{evt.command.action}</span>
                                            <span className="text-zinc-500">→</span>
                                            <span className="text-zinc-300">{evt.command.target}</span>
                                        </div>

                                        <p className="text-[11px] text-zinc-400 leading-relaxed mb-2 font-mono">
                                            {evt.reasoning}
                                        </p>

                                        {evt.conditions.length > 0 && (
                                            <div className="mt-3 border-t border-white/5 pt-2">
                                                <span className="text-[9px] text-emerald-600 uppercase tracking-widest font-semibold block mb-1">Conditions Attached</span>
                                                <ul className="list-none space-y-1">
                                                    {evt.conditions.map((c, i) => (
                                                        <li key={i} className="text-[10px] text-emerald-400/80 font-mono flex gap-2">
                                                            <span className="text-emerald-500">›</span> {c}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    )}
                </div>
            </div>
        </div>
    );
}
