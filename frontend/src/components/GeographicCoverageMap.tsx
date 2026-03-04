/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import { NetworkNode, SegmentType } from '../types';
import { INITIAL_NODES } from '../constants';
import { X, Signal, Clock, HardDrive, Cpu } from 'lucide-react';

interface GeographicCoverageMapProps {
  nodes: NetworkNode[];
  activeSegment: SegmentType | 'ALL';
}

export const GeographicCoverageMap: React.FC<GeographicCoverageMapProps> = ({ nodes, activeSegment }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [worldData, setWorldData] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number, y: number } | null>(null);

  useEffect(() => {
    setSelectedNode(null);
  }, [activeSegment]);

  useEffect(() => {
    // Fetch world map data
    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(response => response.json())
      .then(data => setWorldData(data));
  }, []);

  useEffect(() => {
    if (!svgRef.current || !worldData) return;

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Mercator projection centered on Europe
    const projection = d3.geoMercator()
      .center([10, 50])
      .scale(width * 0.8)
      .translate([width / 2, height / 2]);

    const path = d3.geoPath().projection(projection);

    // Draw map background
    const g = svg.append('g');

    // Draw countries
    const countries = topojson.feature(worldData, worldData.objects.countries);

    g.append('path')
      .datum(countries)
      .attr('d', path as any)
      .attr('fill', '#111116')
      .attr('stroke', '#1e1e24')
      .attr('stroke-width', 0.5);

    // Draw coverage areas (Line of Sight)
    const coverageG = svg.append('g').attr('class', 'coverage-layer');

    nodes.forEach(node => {
      if (activeSegment !== 'ALL' && node.type !== activeSegment) return;

      const [x, y] = projection([node.location.lng, node.location.lat]) || [0, 0];

      // Coverage radius based on type
      let radiusKm = 80;
      if (node.type === 'DOMESTIC') radiusKm = 120;
      if (node.type === 'OVERSEAS') radiusKm = 200;
      if (node.type === 'MARITIME') radiusKm = 250;
      if (node.type === 'SPACE') radiusKm = 500;

      // Convert km to pixels at this scale
      const radiusPx = (radiusKm / 111) * (width * 0.8 / 360) * Math.PI;

      const color = node.type === 'DOMESTIC' ? '#3b82f6' :
                    node.type === 'OVERSEAS' ? '#8b5cf6' :
                    node.type === 'MARITIME' ? '#f59e0b' :
                    '#ec4899';

      // Coverage circle
      coverageG.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', radiusPx)
        .attr('fill', color)
        .attr('fill-opacity', 0.1)
        .attr('stroke', color)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,2')
        .attr('class', 'animate-pulse');

      // Node point
      coverageG.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', 5)
        .attr('fill', color)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .attr('cursor', 'pointer')
        .attr('class', 'hover:scale-150 transition-transform duration-200')
        .on('click', (event) => {
          event.stopPropagation();
          setSelectedNode(node);
          setTooltipPos({ x: event.pageX, y: event.pageY });
        });

      // Status dot
      const statusColor = node.status === 'ONLINE' ? '#10b981' :
                          node.status === 'OFFLINE' ? '#ef4444' :
                          node.status === 'DEGRADED' ? '#f59e0b' :
                          '#3b82f6'; // SURGE

      coverageG.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', 2)
        .attr('fill', statusColor)
        .attr('pointer-events', 'none');
    });

    // EU-scale blind spots
    const gaps = [
      { name: 'Baltic Coverage Gap', lng: 22.0, lat: 56.5 },
      { name: 'Adriatic Blind Spot', lng: 17.0, lat: 44.0 },
      { name: 'Iberian Shadow Zone', lng: -6.0, lat: 39.0 }
    ];

    gaps.forEach(gap => {
      const [x, y] = projection([gap.lng, gap.lat]) || [0, 0];
      svg.append('g')
        .attr('transform', `translate(${x}, ${y})`)
        .call(g => {
          g.append('circle')
            .attr('r', 4)
            .attr('fill', '#ef4444')
            .attr('fill-opacity', 0.5);
          g.append('text')
            .text('BLIND SPOT')
            .attr('x', 8)
            .attr('y', 4)
            .attr('fill', '#ef4444')
            .attr('font-size', '8px')
            .attr('font-family', 'monospace')
            .attr('font-weight', 'bold');
        });
    });

    // Zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([1, 8])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        svg.selectAll('.coverage-layer').attr('transform', event.transform);
      });

    svg.call(zoom as any);
    svg.on('click', () => setSelectedNode(null));

  }, [worldData, nodes, activeSegment]);

  return (
    <div className="w-full h-full bg-[#050507] relative overflow-hidden border border-[#1e1e24] rounded-lg">
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2 bg-black/60 p-3 rounded border border-[#1e1e24] backdrop-blur-sm">
        <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1">Coverage Metrics</div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-[10px] text-zinc-400 font-mono">EU Coverage:</span>
          <span className="text-[10px] text-emerald-400 font-mono font-bold">78.4%</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-[10px] text-zinc-400 font-mono">Blind Spots:</span>
          <span className="text-[10px] text-red-400 font-mono font-bold">3 Detected</span>
        </div>
        <div className="h-px bg-[#1e1e24] my-1" />
        <div className="text-[8px] text-zinc-600 font-mono leading-tight">
          * Line-of-sight calculated at 15° elevation mask.
        </div>
      </div>
      <svg ref={svgRef} className="w-full h-full cursor-move" />

      {selectedNode && tooltipPos && (
        <div
          className="fixed z-50 w-64 bg-[#0d0d12] border border-[#1e1e24] rounded-lg shadow-2xl p-4 pointer-events-auto animate-in fade-in zoom-in duration-200"
          style={{
            left: Math.min(window.innerWidth - 270, tooltipPos.x + 10),
            top: Math.min(window.innerHeight - 200, tooltipPos.y + 10)
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="text-[10px] text-zinc-500 font-mono tracking-widest leading-none mb-1">{selectedNode.id}</div>
              <h3 className="text-sm font-bold text-white tracking-tight">{selectedNode.name}</h3>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[8px] text-zinc-500 font-mono tracking-tighter">
                <Signal className="w-2.5 h-2.5" /> SIGNAL
              </div>
              <div className="text-xs font-mono text-zinc-200">{selectedNode.telemetry.signalStrength}%</div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[8px] text-zinc-500 font-mono tracking-tighter">
                <Clock className="w-2.5 h-2.5" /> LATENCY
              </div>
              <div className="text-xs font-mono text-zinc-200">{selectedNode.telemetry.latency}ms</div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[8px] text-zinc-500 font-mono tracking-tighter">
                <HardDrive className="w-2.5 h-2.5" /> BW
              </div>
              <div className="text-xs font-mono text-zinc-200">{selectedNode.telemetry.bandwidth}G</div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[8px] text-zinc-500 font-mono tracking-tighter">
                <Cpu className="w-2.5 h-2.5" /> CPU
              </div>
              <div className="text-xs font-mono text-zinc-200">{selectedNode.telemetry.cpuLoad}%</div>
            </div>
          </div>

          <div className={`px-2 py-1 rounded text-[9px] font-bold tracking-widest text-center
            ${selectedNode.status === 'ONLINE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
              selectedNode.status === 'SURGE' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
              selectedNode.status === 'DEGRADED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
              'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
            STATUS: {selectedNode.status}
          </div>
        </div>
      )}
    </div>
  );
};
