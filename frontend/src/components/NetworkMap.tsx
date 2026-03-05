/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import ForceGraph3D, { ForceGraphMethods } from 'react-force-graph-3d';
import * as THREE from 'three';
import { NetworkNode, SegmentType } from '../types';

interface NetworkMapProps {
  nodes: NetworkNode[];
  activeSegment: SegmentType | 'AGENTS' | 'SIGINT';
  edges?: { from_bus: number; to_bus: number; loading_percent: number }[];
}

// ── Glow sprite texture (generated once) ──
const createGlowTexture = (): THREE.Texture => {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, 'rgba(255,255,255,0.6)');
  gradient.addColorStop(0.2, 'rgba(255,255,255,0.3)');
  gradient.addColorStop(0.5, 'rgba(255,255,255,0.05)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
};

let _glowTexture: THREE.Texture | null = null;
const getGlowTexture = () => {
  if (!_glowTexture) _glowTexture = createGlowTexture();
  return _glowTexture;
};

// Color helpers
const STATUS_COLORS: Record<string, { hex: string; three: number }> = {
  CRITICAL: { hex: '#ef4444', three: 0xef4444 },
  WARNING: { hex: '#eab308', three: 0xeab308 },
  NOMINAL: { hex: '#10b981', three: 0x10b981 },
};

const getStatusColor = (status: string) => STATUS_COLORS[status] || STATUS_COLORS.NOMINAL;

export const NetworkMap: React.FC<NetworkMapProps> = ({ nodes, activeSegment, edges }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods>();
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 });
  const prevFingerprintRef = useRef<string>('');
  const hasInitializedRef = useRef(false);
  const sceneSetupRef = useRef(false);
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });

  // ── Resize observer ──
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setDimensions({ width, height });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // ── Only rebuild graphData when topology changes ──
  useEffect(() => {
    const nodeIds = nodes.map(n => n.id).sort().join(',');
    const edgeIds = edges ? edges.map(e => `${e.from_bus}-${e.to_bus}`).sort().join(',') : '';
    const fingerprint = `${nodeIds}|${edgeIds}`;
    if (fingerprint === prevFingerprintRef.current) return;
    prevFingerprintRef.current = fingerprint;

    const graphNodes = nodes.map(n => ({ ...n, val: 1 }));
    const links: any[] = [];

    if (edges && edges.length > 0) {
      edges.forEach(e => {
        const srcId = `Bus-${e.from_bus}`;
        const tgtId = `Bus-${e.to_bus}`;
        if (graphNodes.find(n => n.id === srcId) && graphNodes.find(n => n.id === tgtId)) {
          links.push({ source: srcId, target: tgtId, loading: e.loading_percent });
        }
      });
    } else {
      const byZone = new Map<string, typeof graphNodes>();
      graphNodes.forEach(n => {
        const arr = byZone.get(n.type) || [];
        arr.push(n);
        byZone.set(n.type, arr);
      });
      byZone.forEach(zoneNodes => {
        for (let i = 0; i < zoneNodes.length - 1; i++) {
          links.push({ source: zoneNodes[i].id, target: zoneNodes[i + 1].id, loading: 50 });
        }
      });
    }

    setGraphData({ nodes: graphNodes, links });
  }, [nodes, edges]);

  // ── Live Update: Mutate node properties in place to avoid exploding ──
  useEffect(() => {
    if (graphData.nodes.length === 0) return;

    // Map existing graph nodes by ID for fast lookup
    const graphNodeMap = new Map();
    graphData.nodes.forEach((gn: any) => graphNodeMap.set(gn.id, gn));

    let needsUpdate = false;
    nodes.forEach(n => {
      const gNode = graphNodeMap.get(n.id);
      if (gNode) {
        if (gNode.status !== n.status || JSON.stringify(gNode.telemetry) !== JSON.stringify(n.telemetry)) {
          gNode.status = n.status;
          gNode.telemetry = n.telemetry;
          needsUpdate = true;
        }
      }
    });

    if (needsUpdate && fgRef.current) {
      // Tell force graph to re-evaluate node visuals without touching topology/physics
      fgRef.current.refresh();
    }
  }, [nodes, graphData]);

  // ── Configure forces + scene enhancements once ──
  useEffect(() => {
    if (!fgRef.current || graphData.nodes.length === 0 || hasInitializedRef.current) return;
    hasInitializedRef.current = true;

    // Push nodes further apart so they aren't hidden/packed
    fgRef.current.d3Force('charge')?.strength(-90);
    fgRef.current.d3Force('link')?.distance(40);

    setTimeout(() => fgRef.current?.zoomToFit(800, 50), 600);
  }, [graphData]);

  // ── Scene setup: starfield, fog, lighting ──
  useEffect(() => {
    if (!fgRef.current || sceneSetupRef.current) return;
    const scene = fgRef.current.scene();
    if (!scene) return;
    sceneSetupRef.current = true;

    // Starfield particles
    const starCount = 2000;
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      starPositions[i * 3] = (Math.random() - 0.5) * 1200;
      starPositions[i * 3 + 1] = (Math.random() - 0.5) * 1200;
      starPositions[i * 3 + 2] = (Math.random() - 0.5) * 1200;
    }
    starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));

    const starMaterial = new THREE.PointsMaterial({
      color: 0x4488aa,
      size: 0.6,
      transparent: true,
      opacity: 0.5,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    scene.add(new THREE.Points(starGeometry, starMaterial));

    // Grid plane for depth
    const gridHelper = new THREE.GridHelper(400, 40, 0x111122, 0x0a0a18);
    gridHelper.position.y = -80;
    (gridHelper.material as THREE.Material).transparent = true;
    (gridHelper.material as THREE.Material).opacity = 0.15;
    scene.add(gridHelper);

    // Fog for depth (reduced so distant nodes don't completely hide)
    scene.fog = new THREE.FogExp2(0x050508, 0.0005);

    // Lighting
    scene.add(new THREE.AmbientLight(0x222244, 0.6));
    const dirLight = new THREE.DirectionalLight(0x6688cc, 0.8);
    dirLight.position.set(100, 200, 100);
    scene.add(dirLight);
    const pointLight = new THREE.PointLight(0x10b981, 1.5, 300);
    pointLight.position.set(0, 50, 0);
    scene.add(pointLight);
  }, [graphData]);

  // ── Custom node rendering ──
  const nodeThreeObject = useCallback((node: any) => {
    const { three: colorVal, hex } = getStatusColor(node.status);
    const group = new THREE.Group();

    // Core sphere (Basic material so it ignores lighting/shadows and always glows bright)
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(3, 24, 24),
      new THREE.MeshBasicMaterial({
        color: colorVal,
        transparent: true,
        opacity: 0.95,
      })
    );
    group.add(sphere);

    // Inner bright core
    group.add(new THREE.Mesh(
      new THREE.SphereGeometry(1.2, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.7 })
    ));

    // Glow halo sprite (bumped opacity for more pop)
    const spriteMaterial = new THREE.SpriteMaterial({
      map: getGlowTexture(),
      color: colorVal,
      transparent: true,
      opacity: node.status === 'CRITICAL' ? 0.9 : 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(18, 18, 1);
    group.add(sprite);

    // Orbital ring for Zone 1/2 nodes
    if (node.type === 'ZONE 1' || node.type === 'ZONE 2') {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(4.5, 5, 32),
        new THREE.MeshBasicMaterial({ color: colorVal, transparent: true, opacity: 0.6, side: THREE.DoubleSide })
      );
      ring.rotation.x = Math.PI / 2;
      group.add(ring);
    }

    // Floating label (Text)
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 32;
    const ctx = canvas.getContext('2d')!;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = 'bold 22px monospace';
    ctx.fillStyle = hex;
    ctx.textAlign = 'center';
    ctx.fillText(node.id.replace('Bus-', 'B'), 64, 24);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;

    const labelSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: 0.9,
        depthWrite: false,
        blending: THREE.NormalBlending
      })
    );
    labelSprite.scale.set(16, 4, 1);
    labelSprite.position.set(0, 8, 0);
    group.add(labelSprite);

    return group;
  }, []);

  return (
    <div className="w-full h-full bg-[#050508] relative overflow-hidden" ref={containerRef}>
      {/* Vignette overlay */}
      <div className="absolute inset-0 z-[1] pointer-events-none"
        style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.6) 100%)' }}
      />

      {/* Legend Overlay */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-1.5 pointer-events-none">
        <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1">Power Grid Topology (3D)</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'radial-gradient(circle at 30% 30%, #fff, #10b981, #065f46)', boxShadow: '0 0 8px #10b981' }} />
          <span className="text-[10px] font-mono text-zinc-400">Nominal</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'radial-gradient(circle at 30% 30%, #fff, #eab308, #854d0e)', boxShadow: '0 0 8px #eab308' }} />
          <span className="text-[10px] font-mono text-zinc-400">Warning (V ±5%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'radial-gradient(circle at 30% 30%, #fff, #ef4444, #7f1d1d)', boxShadow: '0 0 8px #ef4444' }} />
          <span className="text-[10px] font-mono text-zinc-400">Critical (V ±10%)</span>
        </div>
        <div className="text-[9px] font-mono text-zinc-600 mt-2">
          Drag to Rotate · Scroll to Zoom · Click Node to Focus
        </div>
      </div>

      <div className="absolute inset-0">
        <ForceGraph3D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeId="id"
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
          nodeLabel={(n: any) => `<div style="background:rgba(0,0,0,0.85);border:1px solid ${getStatusColor(n.status).hex};padding:6px 10px;border-radius:6px;font-family:monospace;font-size:11px;color:#e4e4e7;line-height:1.5;backdrop-filter:blur(8px)"><b style="color:${getStatusColor(n.status).hex}">${n.name}</b><br/>V: ${n.telemetry?.voltage || 'N/A'}</div>`}
          linkDirectionalParticles={(l: any) => l.loading > 20 ? 4 : 1}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleColor={(l: any) => l.loading > 80 ? '#fca5a5' : '#6ee7b7'}
          backgroundColor="rgba(0,0,0,0)"
          enableNodeDrag={false}
          onNodeClick={(node: any) => {
            const distance = 80;
            const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
            if (fgRef.current) {
              fgRef.current.cameraPosition(
                { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                node,
                1000
              );
            }
          }}
        />
      </div>
    </div>
  );
};
