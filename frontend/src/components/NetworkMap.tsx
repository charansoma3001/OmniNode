/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { NetworkNode, SegmentType } from '../types';

interface NetworkMapProps {
  nodes: NetworkNode[];
  activeSegment: SegmentType | 'AGENTS' | 'SIGINT';
  edges?: { from_bus: number; to_bus: number; loading_percent: number }[];
}

// Persistent position cache – survives across renders so nodes never "explode"
const positionCache = new Map<string, { x: number; y: number }>();
let hasInitialized = false;

export const NetworkMap: React.FC<NetworkMapProps> = ({ nodes, activeSegment, edges }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<d3.Simulation<any, any> | null>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;
    const svg = d3.select(svgRef.current);

    // ── Build data ──
    const simNodes = nodes.map(n => {
      const cached = positionCache.get(n.id);
      return cached
        ? { ...n, x: cached.x, y: cached.y }
        : { ...n, x: width / 2 + (Math.random() - 0.5) * 200, y: height / 2 + (Math.random() - 0.5) * 200 };
    });

    // Build links from real backend edges, or fallback to same-zone connections
    const links: { source: string; target: string; loading: number }[] = [];
    if (edges && edges.length > 0) {
      edges.forEach(e => {
        const srcId = `Bus-${e.from_bus}`;
        const tgtId = `Bus-${e.to_bus}`;
        // Only include links where both nodes exist in current filtered set
        if (simNodes.find(n => n.id === srcId) && simNodes.find(n => n.id === tgtId)) {
          links.push({ source: srcId, target: tgtId, loading: e.loading_percent });
        }
      });
    } else {
      // Fallback: connect nodes within same zone (limit connections)
      const byZone = new Map<string, typeof simNodes>();
      simNodes.forEach(n => {
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

    // ── Only run the physics simulation on first load ──
    const isFirstLoad = !hasInitialized;

    // Clear previous SVG contents
    svg.selectAll('*').remove();

    // ── Defs: gradients + glow filter ──
    const defs = svg.append('defs');
    const gradients = [
      { id: 'grad-emerald', color: '#10b981' },
      { id: 'grad-blue', color: '#3b82f6' },
      { id: 'grad-amber', color: '#f59e0b' },
      { id: 'grad-gray', color: '#6b7280' },
      { id: 'grad-red', color: '#ef4444' },
      { id: 'grad-yellow', color: '#eab308' },
    ];
    gradients.forEach(c => {
      const g = defs.append('radialGradient').attr('id', c.id).attr('cx', '30%').attr('cy', '30%').attr('r', '70%');
      g.append('stop').attr('offset', '0%').attr('stop-color', '#fff').attr('stop-opacity', 0.7);
      g.append('stop').attr('offset', '45%').attr('stop-color', c.color).attr('stop-opacity', 1);
      g.append('stop').attr('offset', '100%').attr('stop-color', d3.color(c.color)?.darker(2).toString() || '#000').attr('stop-opacity', 1);
    });
    const glowFilter = defs.append('filter').attr('id', 'glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
    glowFilter.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'blur').attr('operator', 'over');

    // ── Container with zoom/pan ──
    const container = svg.append('g');
    const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => container.attr('transform', event.transform));
    svg.call(zoomBehavior);

    // ── Draw links ──
    const linkGroup = container.append('g');
    const linkSelection = linkGroup.selectAll('g.link')
      .data(links)
      .join('g')
      .attr('class', 'link');

    // Base line (dark)
    linkSelection.append('line')
      .attr('stroke', '#1a2332')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.8);

    // Animated energy flow overlay
    linkSelection.append('line')
      .attr('stroke', (d: any) => d.loading > 80 ? '#ef4444' : '#10b981')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6)
      .attr('stroke-dasharray', '6, 10')
      .attr('class', 'animate-flow');

    // ── Draw nodes ──
    const nodeGroup = container.append('g');
    const nodeSelection = nodeGroup.selectAll('g.node')
      .data(simNodes)
      .join('g')
      .attr('class', 'node')
      .attr('transform', (d: any) => `translate(${d.x},${d.y})`)
      .call(d3.drag<SVGGElement, any>()
        .on('start', (event, d) => {
          event.sourceEvent.stopPropagation(); // prevent zoom from firing
          if (simRef.current && !event.active) simRef.current.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x; d.fy = event.y;
          d.x = event.x; d.y = event.y;
          // Move this node visually
          d3.select(event.sourceEvent.target.closest('.node')).attr('transform', `translate(${d.x},${d.y})`);
          // Update connected links
          linkSelection.selectAll('line')
            .attr('x1', (l: any) => l.source.x)
            .attr('y1', (l: any) => l.source.y)
            .attr('x2', (l: any) => l.target.x)
            .attr('y2', (l: any) => l.target.y);
        })
        .on('end', (event, d) => {
          if (simRef.current && !event.active) simRef.current.alphaTarget(0);
          d.fx = null; d.fy = null;
          // Persist dragged position to cache
          positionCache.set(d.id, { x: d.x, y: d.y });
        }));

    // Outer glow ring for critical/warning
    nodeSelection.append('circle')
      .attr('r', (d: any) => d.status === 'CRITICAL' ? 18 : 0)
      .attr('fill', 'none')
      .attr('stroke', '#ef4444')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.5)
      .attr('class', (d: any) => d.status === 'CRITICAL' ? 'animate-ping' : '');

    // Main sphere
    nodeSelection.append('circle')
      .attr('r', 7)
      .attr('fill', (d: any) => {
        if (d.status === 'CRITICAL') return 'url(#grad-red)';
        if (d.status === 'WARNING') return 'url(#grad-yellow)';
        return 'url(#grad-emerald)';
      })
      .attr('stroke', (d: any) => d.status === 'CRITICAL' ? '#fca5a5' : '#1e1e24')
      .attr('stroke-width', 1)
      .attr('filter', (d: any) => d.status !== 'NOMINAL' ? 'url(#glow)' : '')
      .attr('cursor', 'pointer');

    // Short bus ID label (always visible)
    nodeSelection.append('text')
      .text((d: any) => d.id.replace('Bus-', 'B'))
      .attr('x', 11)
      .attr('y', 3)
      .attr('fill', '#6b7280')
      .attr('font-size', '8px')
      .attr('font-family', 'monospace')
      .attr('pointer-events', 'none');

    // Hover tooltip group (hidden by default)
    const tooltip = nodeSelection.append('g')
      .attr('class', 'node-tooltip')
      .attr('opacity', 0)
      .attr('pointer-events', 'none');

    tooltip.append('rect')
      .attr('x', 10)
      .attr('y', -22)
      .attr('width', (d: any) => Math.max(d.name.length, 10) * 6.5 + 12)
      .attr('height', 34)
      .attr('fill', '#0a0a0c')
      .attr('fill-opacity', 0.92)
      .attr('stroke', '#1e1e24')
      .attr('rx', 4);

    tooltip.append('text')
      .text((d: any) => d.name)
      .attr('x', 16)
      .attr('y', -8)
      .attr('fill', '#e4e4e7')
      .attr('font-size', '9px')
      .attr('font-family', 'monospace');

    tooltip.append('text')
      .text((d: any) => d.telemetry?.voltage || '')
      .attr('x', 16)
      .attr('y', 5)
      .attr('fill', (d: any) => d.status === 'CRITICAL' ? '#fca5a5' : '#6b7280')
      .attr('font-size', '8px')
      .attr('font-family', 'monospace');

    nodeSelection.on('mouseover', function () {
      d3.select(this).select('.node-tooltip').transition().duration(150).attr('opacity', 1);
    }).on('mouseout', function () {
      d3.select(this).select('.node-tooltip').transition().duration(150).attr('opacity', 0);
    });

    // ── Tick function ──
    const tick = () => {
      linkSelection.selectAll('line')
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      nodeSelection.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    };

    if (isFirstLoad) {
      // Full simulation on first load – spread out generously
      const sim = d3.forceSimulation(simNodes as any)
        .force('link', d3.forceLink(links).id((d: any) => d.id).distance(160))
        .force('charge', d3.forceManyBody().strength(-250))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(55))
        .on('tick', tick)
        .on('end', () => {
          // Cache final positions for all future renders
          simNodes.forEach((n: any) => positionCache.set(n.id, { x: n.x, y: n.y }));
        });

      simRef.current = sim;
      hasInitialized = true;

      return () => { sim.stop(); };
    } else {
      // Subsequent renders: just use cached positions, no physics
      // Resolve link references manually
      const nodeById = new Map(simNodes.map(n => [n.id, n]));
      links.forEach((l: any) => {
        if (typeof l.source === 'string') l.source = nodeById.get(l.source) || l.source;
        if (typeof l.target === 'string') l.target = nodeById.get(l.target) || l.target;
      });

      // Update positions from cache and re-render
      tick();

      // Cache any new nodes
      simNodes.forEach((n: any) => positionCache.set(n.id, { x: n.x, y: n.y }));
    }
  }, [nodes, activeSegment, edges]);

  return (
    <div className="w-full h-full bg-[#0a0a0c] relative overflow-hidden">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-1.5">
        <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1">Power Grid Topology</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'radial-gradient(circle at 30% 30%, #fff, #10b981, #065f46)' }} />
          <span className="text-[10px] font-mono text-zinc-400">Nominal</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'radial-gradient(circle at 30% 30%, #fff, #eab308, #854d0e)' }} />
          <span className="text-[10px] font-mono text-zinc-400">Warning (V ±5%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'radial-gradient(circle at 30% 30%, #fff, #ef4444, #7f1d1d)' }} />
          <span className="text-[10px] font-mono text-zinc-400">Critical (V ±10%)</span>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <div className="w-6 h-0.5 bg-emerald-500 animate-flow" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #10b981 0 4px, transparent 4px 10px)' }} />
          <span className="text-[10px] font-mono text-zinc-400">Energy Flow</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-0.5 bg-red-500" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #ef4444 0 4px, transparent 4px 10px)' }} />
          <span className="text-[10px] font-mono text-zinc-400">Overloaded Line</span>
        </div>
      </div>
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
};
