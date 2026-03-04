/**
 * Runtime configuration derived from environment variables.
 *
 * NEXT_PUBLIC_WS_URL – WebSocket base URL for the backend.
 *   • Local dev default: ws://localhost:8000
 *   • For Vercel: set to your public backend URL, e.g. wss://your-backend.ngrok.io
 */

const WS_URL =
    process.env.NEXT_PUBLIC_WS_URL?.replace(/\/+$/, '') ?? 'ws://localhost:8000';

export function wsUrl(path: string): string {
    return `${WS_URL}${path}`;
}
