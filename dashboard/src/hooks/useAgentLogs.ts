import { useState, useEffect, useRef } from 'react';
import useWebSocket from 'react-use-websocket';

export interface AgentLog {
    timestamp: string;
    level: 'info' | 'warning' | 'error' | 'analyzing' | 'tool_call' | 'tool_result' | 'decision';
    message: string;
    data?: any;
}

export function useAgentLogs() {
    const [logs, setLogs] = useState<AgentLog[]>([]);

    const { lastJsonMessage } = useWebSocket('ws://localhost:8000/ws/agent_logs', {
        shouldReconnect: () => true,
        reconnectInterval: 3000,
    });

    useEffect(() => {
        if (lastJsonMessage && typeof lastJsonMessage === 'object') {
            const newLog = lastJsonMessage as AgentLog;
            // Keep only last 100 messages
            setLogs((prev) => [...prev, newLog].slice(-100));
        }
    }, [lastJsonMessage]);

    return { logs };
}
