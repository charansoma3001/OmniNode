"use client";

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line, Sphere, Html } from '@react-three/drei';
import * as THREE from 'three';
import { GridPayload } from '@/hooks/useGridState';

interface NodeProps {
    node: GridPayload['nodes'][0];
}

export function GridNode({ node }: NodeProps) {
    const meshRef = useRef<THREE.Mesh>(null);

    // Scale down coordinates to fit nicely in 3D view
    // Using x and z for the 2D plane spread, y=0
    const position = useMemo(() => new THREE.Vector3(node.x * 0.5, 0, node.y * 0.5), [node.x, node.y]);

    // Color logic
    const color = useMemo(() => {
        if (node.vm_pu < 0.90 || node.vm_pu > 1.10) return new THREE.Color('#ef4444'); // Critical (Red)
        if (node.vm_pu < 0.95 || node.vm_pu > 1.05) return new THREE.Color('#eab308'); // Warning (Yellow)
        return new THREE.Color('#3b82f6'); // Nominal (Blue)
    }, [node.vm_pu]);

    // Animate critical nodes pulsing
    useFrame(({ clock }) => {
        if (!meshRef.current) return;
        const isCritical = node.vm_pu < 0.90 || node.vm_pu > 1.10;
        if (isCritical) {
            const scale = 1 + Math.sin(clock.elapsedTime * 5) * 0.2;
            meshRef.current.scale.set(scale, scale, scale);
        } else {
            meshRef.current.scale.set(1, 1, 1);
        }
    });

    return (
        <group position={position}>
            <Sphere ref={meshRef} args={[0.5, 32, 32]}>
                {/* Use emissive glowing material */}
                <meshStandardMaterial
                    color={color}
                    emissive={color}
                    emissiveIntensity={2}
                    toneMapped={false}
                />
            </Sphere>

            {/* HTML Label floating above the node */}
            <Html position={[0, 1.2, 0]} center className="pointer-events-none">
                <div className="bg-black/80 text-white text-[10px] px-2 py-1 rounded border border-white/20 whitespace-nowrap backdrop-blur whitespace-pre text-center">
                    {`Bus ${node.id}\n${node.vm_pu.toFixed(3)}`}
                </div>
            </Html>
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

    // If either node is missing from the data, don't render the line
    if (!fromNode || !toNode) return null;

    const start = useMemo(() => new THREE.Vector3(fromNode.x * 0.5, 0, fromNode.y * 0.5), [fromNode]);
    const end = useMemo(() => new THREE.Vector3(toNode.x * 0.5, 0, toNode.y * 0.5), [toNode]);

    const isCritical = edge.loading_percent > 100;
    const isWarning = edge.loading_percent > 80;

    let color = '#64748b'; // Slate gray
    if (isCritical) color = '#ef4444'; // Red
    else if (isWarning) color = '#eab308'; // Yellow

    const intensity = isCritical ? 5 : (isWarning ? 2 : 1);
    const lineWidth = isCritical ? 4 : (isWarning ? 3 : 1.5);

    return (
        <Line
            points={[start, end]}
            color={color}
            lineWidth={lineWidth}
            dashed={isWarning || isCritical}
            dashSize={isCritical ? 1 : 0}
            dashScale={isCritical ? 0.5 : 1}
            // Add a glow effect to lines via custom materials in post-processing
            material-toneMapped={false}
        />
    );
}
