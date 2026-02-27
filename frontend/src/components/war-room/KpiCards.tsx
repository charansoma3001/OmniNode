"use client";

import { Card } from "@/components/ui/card";
import { useGridState } from "@/hooks/useGridState";

export function KpiCards() {
    const { gridData } = useGridState();

    if (!gridData) {
        return (
            <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(i => (
                    <Card key={i} className="p-4 bg-card/50 border-border/50 backdrop-blur animate-pulse h-20" />
                ))}
            </div>
        );
    }

    // Count active violations
    const violationCount = gridData.violations.length;
    const isHealthy = violationCount === 0;

    return (
        <div className="grid grid-cols-4 gap-4">
            <Card className="p-4 bg-card/50 border-border/50 backdrop-blur">
                <div className="text-sm text-muted-foreground uppercase tracking-wider">Total Generation</div>
                <div className="text-2xl font-bold font-mono mt-1 text-primary">
                    {gridData.total_generation_mw.toFixed(1)} <span className="text-sm text-muted-foreground">MW</span>
                </div>
            </Card>
            <Card className="p-4 bg-card/50 border-border/50 backdrop-blur">
                <div className="text-sm text-muted-foreground uppercase tracking-wider">Total Load</div>
                <div className="text-2xl font-bold font-mono mt-1 text-primary">
                    {gridData.total_load_mw.toFixed(1)} <span className="text-sm text-muted-foreground">MW</span>
                </div>
            </Card>
            <Card className="p-4 bg-card/50 border-border/50 backdrop-blur">
                <div className="text-sm text-muted-foreground uppercase tracking-wider">Frequency</div>
                <div className="text-2xl font-bold font-mono mt-1 text-primary">
                    {gridData.frequency_hz.toFixed(2)} <span className="text-sm text-muted-foreground">Hz</span>
                </div>
            </Card>
            <Card className="p-4 bg-card/50 border-border/50 backdrop-blur flex flex-col justify-center">
                <div className="text-sm text-muted-foreground uppercase tracking-wider">System Health</div>
                <div className={`text-2xl font-bold mt-1 tracking-wide uppercase ${isHealthy ? 'text-emerald-500' : 'text-destructive animate-pulse'}`}>
                    {isHealthy ? 'Nominal' : `${violationCount} Violations`}
                </div>
            </Card>
        </div>
    );
}
