import { useState, useEffect } from 'react';
import useWebSocket from 'react-use-websocket';

export interface GuardianEvent {
    timestamp: string;
    command: {
        action: string;
        target: string;
        parameters: any;
    };
    safe: boolean;
    risk_level: string;
    reasoning: string;
    conditions: string[];
}

export function useGuardianEvents() {
    const [events, setEvents] = useState<GuardianEvent[]>([]);

    const { lastJsonMessage } = useWebSocket('ws://localhost:8000/ws/guardian_events', {
        shouldReconnect: () => true,
        reconnectInterval: 3000,
    });

    useEffect(() => {
        if (lastJsonMessage && typeof lastJsonMessage === 'object') {
            const newEvent = lastJsonMessage as GuardianEvent;
            // Keep only last 10 messages
            setEvents((prev) => [newEvent, ...prev].slice(0, 10)); // Prepend for latest-first
        }
    }, [lastJsonMessage]);

    return { events };
}
