"use client";

import { useGuardianEvents } from "@/hooks/useGuardianEvents";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, ShieldCheck } from "lucide-react";

export function GuardianPanel() {
    const { events } = useGuardianEvents();

    return (
        <div className="flex-1 flex flex-col bg-card rounded-xl border border-border/50 overflow-hidden shadow-lg h-full">
            <div className="h-10 border-b border-border/50 bg-muted/20 flex items-center px-4 flex-none gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase">
                    Guardian Intercept
                </h2>
            </div>

            <ScrollArea className="flex-1 p-4">
                <div className="flex flex-col gap-3">
                    {events.length === 0 ? (
                        <div className="text-sm text-muted-foreground italic p-4 text-center">
                            Monitoring command stream...
                        </div>
                    ) : (
                        <AnimatePresence>
                            {events.map((evt, idx) => (
                                <motion.div
                                    key={`${evt.timestamp}-${idx}`}
                                    initial={{ opacity: 0, x: -20, height: 0 }}
                                    animate={{ opacity: 1, x: 0, height: "auto" }}
                                    className="overflow-hidden"
                                >
                                    <Card className={`p-3 border text-sm ${evt.safe ? 'bg-emerald-950/20 border-emerald-900/50' : 'bg-destructive/20 border-destructive/50'}`}>
                                        <div className="flex items-start justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                {evt.safe ? (
                                                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                                                ) : (
                                                    <ShieldAlert className="h-4 w-4 text-destructive animate-pulse" />
                                                )}
                                                <span className={`font-semibold ${evt.safe ? 'text-emerald-500' : 'text-destructive'}`}>
                                                    {evt.safe ? "APPROVED" : "BLOCKED"}
                                                </span>
                                            </div>
                                            <Badge variant={evt.safe ? 'outline' : 'destructive'} className="text-[10px] lowercase">
                                                {evt.risk_level} risk
                                            </Badge>
                                        </div>

                                        <div className="font-mono text-xs text-muted-foreground mb-2 p-2 bg-background/50 rounded rounded-md">
                                            <span className="text-primary">{evt.command.action}</span>
                                            <span className="mx-1">on</span>
                                            <span className="text-secondary-foreground">{evt.command.target}</span>
                                        </div>

                                        <p className="text-xs text-foreground/80 leading-relaxed mb-2">
                                            {evt.reasoning}
                                        </p>

                                        {evt.conditions.length > 0 && (
                                            <div className="mt-2 border-t border-border/30 pt-2">
                                                <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold block mb-1">Conditions</span>
                                                <ul className="list-disc list-inside text-xs text-muted-foreground">
                                                    {evt.conditions.map((c, i) => (
                                                        <li key={i}>{c}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </Card>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    )}
                </div>
            </ScrollArea>
        </div>
    );
}
