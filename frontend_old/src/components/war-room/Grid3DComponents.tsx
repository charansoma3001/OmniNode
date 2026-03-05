"use client";

import { useMemo, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line, Sphere, Html } from '@react-three/drei';
import * as THREE from 'three';
import { GridPayload } from '@/hooks/useGridState';

interface NodeProps {
    node: GridPayload['nodes'][0];
}

export function GridNode({ node }: NodeProps) {
    const meshRef = useRef<THREE.Mesh>(null);
    const [hovered, setHovered] = useState(false);

    // Scale down coordinates to fit nicely in 3D view
    const position = useMemo(() => new THREE.Vector3(node.x * 0.5, 0, node.y * 0.5), [node.x, node.y]);

    // Color logic
    const color = useMemo(() => {
        if (node.vm_pu < 0.90 || node.vm_pu > 1.10) return new THREE.Color('#ef4444'); // Critical (Red)
        if (node.vm_pu < 0.95 || node.vm_pu > 1.05) return new THREE.Color('#eab308'); // Warning (Yellow)
        return new THREE.Color('#3b82f6'); // Nominal (Blue)
    }, [node.vm_pu]);

    // Animate critical nodes pulsing and hover scaling
    useFrame(({ clock }) => {
        if (!meshRef.current) return;
        const isCritical = node.vm_pu < 0.90 || node.vm_pu > 1.10;

        let targetScale = 1;
        if (isCritical) {
            targetScale = 1 + Math.sin(clock.elapsedTime * 6) * 0.25;
        } else if (hovered) {
            targetScale = 1.2;
        }

        // Smooth scale interpolation
        meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
    });

    return (
        <group position={position}>
            <Sphere
                ref={meshRef}
                args={[0.5, 32, 32]}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
            >
                {/* Use emissive glowing material */}
                <meshStandardMaterial
                    color={color}
                    emissive={color}
                    emissiveIntensity={hovered ? 3 : 2}
                    toneMapped={false}
                    roughness={0.2}
                    metalness={0.8}
                />
            </Sphere>

            {/* HTML Label floating above the node - Only show on Hover in Cyberpunk mode */}
            {hovered && (
                <Html position={[0, 1.5, 0]} center className="pointer-events-none z-50">
                    <div className="bg-black/80 text-cyan-400 text-xs px-3 py-2 rounded-md border border-cyan-500/50 whitespace-nowrap backdrop-blur-md shadow-[0_0_15px_rgba(34,211,238,0.4)] transition-opacity duration-200">
                        <div className="font-bold border-b border-cyan-500/30 pb-1 mb-1">Bus {node.id}</div>
                        <div className="text-[10px] text-zinc-300">Voltage: <span className="font-mono text-white">{node.vm_pu.toFixed(3)} pu</span></div>
                    </div>
                </Html>
            )}
        </group>
    );
}

interface EdgeProps {
    edge: GridPayload['edges'][0];
    nodesMap: Map<number, GridPayload['nodes'][0]>;
}

export function GridEdge({ edge, nodesMap }: EdgeProps) {
    const fromNode = nodesMap.get(edge.from_bus);
    const toNode = nodesMap.get(edge.to_bus);
    const lineRef = useRef<any>(null);

    // If either node is missing from the data, don't render the line
    if (!fromNode || !toNode) return null;

    const start = useMemo(() => new THREE.Vector3(fromNode.x * 0.5, 0, fromNode.y * 0.5), [fromNode]);
    const end = useMemo(() => new THREE.Vector3(toNode.x * 0.5, 0, toNode.y * 0.5), [toNode]);

    const isCritical = edge.loading_percent > 100;
    const isWarning = edge.loading_percent > 80;

    let color = '#64748b'; // Slate gray
    if (isCritical) color = '#ef4444'; // Red
    else if (isWarning) color = '#eab308'; // Yellow

    const lineWidth = isCritical ? 5 : (isWarning ? 3 : 1.5);

    // Animate the dashed lines flowing to simulate power flow
    useFrame(({ clock }) => {
        if (lineRef.current && lineRef.current.material) {
            // Negative speed makes it flow from start to end (usually)
            lineRef.current.material.dashOffset -= (isCritical ? 0.05 : 0.02);
        }
    });

    return (
        <Line
            ref={lineRef}
            points={[start, end]}
            color={color}
            lineWidth={lineWidth}
            dashed={true}
            dashSize={isCritical ? 1.5 : 0.5}
            dashScale={isCritical ? 0.5 : 1}
            // Add a glow effect to lines via custom materials in post-processing
            material-toneMapped={false}
        />
    );
}
