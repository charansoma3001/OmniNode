"use client";

import { Badge } from "@/components/ui/badge";

export function DomainSwitcher() {
    return (
        <div className="flex items-center gap-2 bg-muted/20 p-1 rounded-lg border border-border/50">
            <Badge variant="secondary" className="bg-primary/20 text-primary hover:bg-primary/30 cursor-pointer">
                Power Grid
            </Badge>
            <Badge variant="outline" className="text-muted-foreground cursor-not-allowed opacity-50">
                Robotics
            </Badge>
            <Badge variant="outline" className="text-muted-foreground cursor-not-allowed opacity-50">
                Satellite
            </Badge>
        </div>
    );
}
