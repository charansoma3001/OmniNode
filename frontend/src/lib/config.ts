/**
 * Runtime configuration derived from environment variables.
 *
 * VITE_WS_URL – WebSocket base URL for the backend.
 *   • Local dev default: ws://localhost:8000
 */

const WS_URL =
    import.meta.env?.VITE_WS_URL?.replace(/\/+$/, '') ?? 'ws://localhost:8000';

export function wsUrl(path: string): string {
    return `${WS_URL}${path}`;
}
