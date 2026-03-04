"use client";

import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, Grid } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { useGridState } from '@/hooks/useGridState';
import { GridNode, GridEdge } from './Grid3DComponents';

export function TopologyMap() {
    const { gridData } = useGridState();

    const nodesMap = useMemo(() => {
        if (!gridData) return new Map();
        return new Map(gridData.nodes.map(n => [n.id, n]));
    }, [gridData]);

    if (!gridData) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-black">
                <p className="text-muted-foreground animate-pulse">Connecting to Backend...</p>
            </div>
        );
    }

    return (
        <div className="w-full h-full relative bg-black">
            <div className="absolute top-4 left-4 z-10 bg-black/80 backdrop-blur border border-white/10 p-2 rounded-md shadow-[0_0_15px_rgba(59,130,246,0.3)]">
                <h3 className="text-sm font-semibold text-blue-400">3D Live Topology</h3>
                <p className="text-xs text-muted-foreground">IEEE 30-Bus System</p>

                {/* Legend */}
                <div className="mt-2 space-y-1">
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_5px_#3b82f6]"></span><span className="text-[10px] text-zinc-400">Nominal</span></div>
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-yellow-400 shadow-[0_0_5px_#eab308]"></span><span className="text-[10px] text-zinc-400">Warning (Voltage)</span></div>
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_5px_#ef4444] animate-pulse"></span><span className="text-[10px] text-zinc-400">Critical (Voltage/Load)</span></div>
                </div>
            </div>

            <Canvas camera={{ position: [0, 15, 20], fov: 45 }}>
                <color attach="background" args={['#050505']} />

                {/* Scene Lighting */}
                <ambientLight intensity={0.5} />
                <directionalLight position={[10, 20, 10]} intensity={1} />

                {/* Grid Floor */}
                <Grid
                    position={[0, -1, 0]}
                    args={[100, 100]}
                    cellSize={1}
                    cellThickness={0.5}
                    cellColor="#1a1a1a"
                    sectionSize={5}
                    sectionThickness={1}
                    sectionColor="#333"
                    fadeDistance={30}
                    fadeStrength={1}
                />

                {/* Grid Elements */}
                <group>
                    {gridData.edges.map(e => (
                        <GridEdge key={`edge-${e.id}`} edge={e} nodesMap={nodesMap} />
                    ))}
                    {gridData.nodes.map(n => (
                        <GridNode key={`node-${n.id}`} node={n} />
                    ))}
                </group>

                {/* Camera Controls */}
                <OrbitControls
                    makeDefault
                    minPolarAngle={0}
                    maxPolarAngle={Math.PI / 2 - 0.1} // Prevent going below the floor
                    enableDamping
                    dampingFactor={0.05}
                />

                {/* Glowing Effects */}
                <EffectComposer>
                    {/* Bloom makes intense colors spread out like neon lights */}
                    <Bloom
                        luminanceThreshold={0.5}
                        mipmapBlur
                        intensity={2.5}
                    />
                </EffectComposer>
            </Canvas>
        </div>
    );
}
