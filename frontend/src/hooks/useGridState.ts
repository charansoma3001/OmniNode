import { useState, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

export interface GridPayload {
    timestamp: string;
    total_generation_mw: number;
    total_load_mw: number;
    total_losses_mw: number;
    frequency_hz: number;
    nodes: { id: number; vm_pu: number; x: number; y: number; zone: string }[];
    edges: { id: number; loading_percent: number; from_bus: number; to_bus: number }[];
    zone_health: Record<string, string>;
    violations: any[];
}

export function useGridState() {
    const [gridData, setGridData] = useState<GridPayload | null>(null);

    // Auto-reconnecting WebSocket
    const { lastJsonMessage, readyState } = useWebSocket('ws://localhost:8000/ws/grid_state', {
        shouldReconnect: () => true,
        reconnectInterval: 3000,
        reconnectAttempts: 100,
    });

    useEffect(() => {
        if (lastJsonMessage && typeof lastJsonMessage === 'object') {
            setGridData(lastJsonMessage as GridPayload);
        }
    }, [lastJsonMessage]);

    return { gridData, readyState };
}
