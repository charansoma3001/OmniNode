/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Ship, Satellite, Radio, Brain, Activity, Waves, Globe } from 'lucide-react';

interface DomainPlaceholderProps {
    domain: 'DOMESTIC' | 'MARITIME' | 'SPACE' | 'PIGNN';
}

const domainConfig = {
    DOMESTIC: {
        icon: Radio,
        title: 'Domestic Ground Stations',
        subtitle: 'Core Western Europe Infrastructure',
        color: 'blue',
        stats: [
            { label: 'Sensor Servers', value: '11', status: 'online' },
            { label: 'Actuator Servers', value: '5', status: 'online' },
            { label: 'Coverage', value: '97.3%', status: 'nominal' },
            { label: 'Avg Latency', value: '12ms', status: 'nominal' },
        ],
        nodes: [
            { name: 'London Hub', status: 'NOMINAL', lat: '51.5°N', lng: '0.1°W' },
            { name: 'Paris Relay', status: 'NOMINAL', lat: '48.9°N', lng: '2.3°E' },
            { name: 'Berlin Station', status: 'NOMINAL', lat: '52.5°N', lng: '13.4°E' },
            { name: 'Amsterdam Core', status: 'NOMINAL', lat: '52.4°N', lng: '4.9°E' },
            { name: 'Brussels Node', status: 'WARNING', lat: '50.8°N', lng: '4.4°E' },
            { name: 'Madrid Gateway', status: 'NOMINAL', lat: '40.4°N', lng: '3.7°W' },
        ],
        description: 'Monitors voltage, frequency, and power quality across core hub infrastructure. Covers London, Paris, Berlin, Amsterdam, Brussels, and Madrid ground stations.',
    },
    MARITIME: {
        icon: Ship,
        title: 'Maritime Corridor',
        subtitle: 'Ship-based & Buoy Sensor Networks',
        color: 'cyan',
        stats: [
            { label: 'Active Buoys', value: '47', status: 'online' },
            { label: 'Ship Nodes', value: '12', status: 'online' },
            { label: 'Sea Coverage', value: '89.1%', status: 'nominal' },
            { label: 'Wave Height', value: '1.8m', status: 'nominal' },
        ],
        nodes: [
            { name: 'North Sea Alpha', status: 'NOMINAL', lat: '56.0°N', lng: '3.0°E' },
            { name: 'Baltic Gateway', status: 'NOMINAL', lat: '55.7°N', lng: '12.6°E' },
            { name: 'Mediterranean-W', status: 'WARNING', lat: '38.7°N', lng: '0.5°W' },
            { name: 'Mediterranean-E', status: 'NOMINAL', lat: '35.3°N', lng: '24.5°E' },
            { name: 'Channel Relay', status: 'NOMINAL', lat: '50.3°N', lng: '1.0°W' },
            { name: 'Atlantic Buoy-3', status: 'NOMINAL', lat: '48.5°N', lng: '6.8°W' },
        ],
        description: 'Ocean corridor positioning and environmental monitoring across the North Sea, Mediterranean, and Baltic corridors. Geolocation accuracy: ±1.2m.',
    },
    SPACE: {
        icon: Satellite,
        title: 'Space Segment',
        subtitle: 'Geostationary & Polar Relay Network',
        color: 'purple',
        stats: [
            { label: 'Satellites', value: '3', status: 'online' },
            { label: 'Polar Relays', value: '2', status: 'online' },
            { label: 'Arctic Stations', value: '2', status: 'nominal' },
            { label: 'Link Budget', value: '+4.2dB', status: 'nominal' },
        ],
        nodes: [
            { name: 'GEO-SAT-1 (10°E)', status: 'NOMINAL', lat: '0.0°', lng: '10.0°E' },
            { name: 'GEO-SAT-2 (25°E)', status: 'NOMINAL', lat: '0.0°', lng: '25.0°E' },
            { name: 'POLAR-RELAY-N', status: 'NOMINAL', lat: '78.2°N', lng: '15.6°E' },
            { name: 'POLAR-RELAY-S', status: 'WARNING', lat: '71.0°S', lng: '2.5°W' },
            { name: 'Svalbard Ground', status: 'NOMINAL', lat: '78.2°N', lng: '15.6°E' },
            { name: 'Tromsø Station', status: 'NOMINAL', lat: '69.6°N', lng: '19.0°E' },
        ],
        description: 'Geostationary satellites, polar relay monitoring, and Arctic ground station management. Provides continuous global coverage with 99.98% uptime SLA.',
    },
    PIGNN: {
        icon: Brain,
        title: 'PI-GNN Surrogate Model',
        subtitle: 'Physics-Informed Graph Neural Network',
        color: 'amber',
        stats: [
            { label: 'Inference Time', value: '0.8ms', status: 'nominal' },
            { label: 'Accuracy', value: '99.2%', status: 'nominal' },
            { label: 'Speedup', value: '127×', status: 'online' },
            { label: 'Model Version', value: 'v2.1', status: 'nominal' },
        ],
        nodes: [
            { name: 'Voltage Predictor', status: 'NOMINAL', lat: '', lng: '' },
            { name: 'Flow Estimator', status: 'NOMINAL', lat: '', lng: '' },
            { name: 'Stability Classifier', status: 'NOMINAL', lat: '', lng: '' },
            { name: 'Contingency Ranker', status: 'NOMINAL', lat: '', lng: '' },
            { name: 'Loss Predictor', status: 'NOMINAL', lat: '', lng: '' },
            { name: 'Frequency Estimator', status: 'WARNING', lat: '', lng: '' },
        ],
        description: 'Augments Pandapower IEEE 30-bus simulation with faster-than-real-time prediction. Graph attention layers learn bus-level physics constraints for N-1 contingency screening at 127× speedup over full AC power flow.',
    },
};

const colorMap: Record<string, { bg: string; border: string; text: string; dot: string; glow: string }> = {
    blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-400', dot: 'bg-blue-500', glow: 'shadow-blue-500/20' },
    cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', text: 'text-cyan-400', dot: 'bg-cyan-500', glow: 'shadow-cyan-500/20' },
    purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400', dot: 'bg-purple-500', glow: 'shadow-purple-500/20' },
    amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', dot: 'bg-amber-500', glow: 'shadow-amber-500/20' },
};

export const DomainPlaceholder: React.FC<DomainPlaceholderProps> = ({ domain }) => {
    const config = domainConfig[domain];
    const colors = colorMap[config.color];
    const Icon = config.icon;

    return (
        <div className="p-8 h-full flex flex-col gap-6 overflow-auto">
            {/* Header */}
            <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center`}>
                    <Icon className={`w-6 h-6 ${colors.text}`} />
                </div>
                <div>
                    <h2 className="text-lg font-bold text-white tracking-tight">{config.title}</h2>
                    <p className="text-xs text-zinc-500 font-mono mt-0.5">{config.subtitle}</p>
                </div>
                <div className="ml-auto flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[10px] font-bold text-emerald-400 tracking-widest uppercase">Online</span>
                </div>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-4 gap-4">
                {config.stats.map(stat => (
                    <div key={stat.label} className="bg-[#0a0a0c] border border-[#1e1e24] rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider">{stat.label}</span>
                            <div className={`w-1.5 h-1.5 rounded-full ${stat.status === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-emerald-500'}`} />
                        </div>
                        <span className="text-xl font-bold text-white font-mono">{stat.value}</span>
                    </div>
                ))}
            </div>

            {/* Description */}
            <div className={`${colors.bg} ${colors.border} border rounded-lg p-4`}>
                <p className="text-xs text-zinc-300 leading-relaxed">{config.description}</p>
            </div>

            {/* Node Table */}
            <div className="bg-[#0a0a0c] border border-[#1e1e24] rounded-lg overflow-hidden flex-1">
                <div className="px-4 py-3 border-b border-[#1e1e24] flex items-center justify-between">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
                        {domain === 'PIGNN' ? 'Model Components' : 'Active Nodes'}
                    </span>
                    <span className={`text-[10px] font-mono ${colors.text}`}>{config.nodes.length} total</span>
                </div>
                <div className="divide-y divide-[#1e1e24]">
                    {config.nodes.map((node, i) => (
                        <div key={i} className="px-4 py-3 flex items-center gap-3 hover:bg-white/[0.02] transition-colors">
                            <div className={`w-2 h-2 rounded-full ${node.status === 'CRITICAL' ? 'bg-red-500' :
                                    node.status === 'WARNING' ? 'bg-amber-500' : 'bg-emerald-500'
                                }`} />
                            <span className="text-xs text-white font-medium flex-1">{node.name}</span>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${node.status === 'WARNING'
                                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                    : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                                }`}>
                                {node.status}
                            </span>
                            {node.lat && (
                                <span className="text-[9px] font-mono text-zinc-600 w-28 text-right">{node.lat}, {node.lng}</span>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
