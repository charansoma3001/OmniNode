"use client";

import { useMemo } from 'react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useGridState } from '@/hooks/useGridState';

export function TopologyMap() {
    const { gridData } = useGridState();

    const nodes = useMemo(() => {
        if (!gridData) return [{ id: '1', position: { x: 0, y: 0 }, data: { label: 'Connecting to Backend...' } }];
        return gridData.nodes.map(n => {
            // Color coding based on voltage limits
            let bgColor = '#3b82f6'; // Blue for nominal
            if (n.vm_pu < 0.95 || n.vm_pu > 1.05) bgColor = '#eab308'; // Yellow for warning
            if (n.vm_pu < 0.90 || n.vm_pu > 1.10) bgColor = '#ef4444'; // Red for critical

            return {
                id: n.id.toString(),
                position: { x: n.x, y: n.y },
                data: { label: `Bus ${n.id}\n${n.vm_pu.toFixed(3)}` },
                style: {
                    backgroundColor: bgColor,
                    color: '#fff',
                    border: '2px solid #1e293b',
                    borderRadius: '50%',
                    width: 50,
                    height: 50,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '10px',
                    fontWeight: 'bold',
                    textAlign: 'center'
                }
            };
        });
    }, [gridData]);

    const edges = useMemo(() => {
        if (!gridData) return [];
        return gridData.edges.map(e => ({
            id: `e-${e.id}-${e.from_bus}-${e.to_bus}`,
            source: e.from_bus.toString(),
            target: e.to_bus.toString(),
            animated: e.loading_percent > 80, // Animate high load edges
            style: { stroke: e.loading_percent > 100 ? '#ef4444' : '#64748b', strokeWidth: e.loading_percent > 80 ? 3 : 2 }
        }));
    }, [gridData]);

    return (
        <div className="w-full h-full text-foreground relative">
            <div className="absolute top-4 left-4 z-10 bg-card/80 backdrop-blur border border-border/50 p-2 rounded-md shadow-md">
                <h3 className="text-sm font-semibold text-primary">Live Topology</h3>
                <p className="text-xs text-muted-foreground">IEEE 30-Bus System</p>
            </div>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                colorMode="dark"
                minZoom={0.1}
            >
                <Background gap={12} size={1} />
                <Controls />
            </ReactFlow>
        </div>
    );
}
