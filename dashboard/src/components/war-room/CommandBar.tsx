"use client";

import { useState } from "react";
import useWebSocket from "react-use-websocket";
import { Send } from "lucide-react";

export function CommandBar() {
    const [input, setInput] = useState("");

    const { sendMessage } = useWebSocket('ws://localhost:8000/ws/commands', {
        shouldReconnect: () => true,
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        // Parse commands for demo
        let action = "nl_query";
        let payload = input;

        if (input.startsWith("scenario ")) {
            action = "trigger_scenario";
            payload = input.replace("scenario ", "");
        } else if (input.trim().toLowerCase() === "rollback") {
            action = "rollback";
            payload = "";
        }

        sendMessage(JSON.stringify({ action, payload }));
        setInput("");
    };

    return (
        <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto flex items-center">
            <div className="relative w-full group">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3">
                    <span className="text-primary font-bold">{">"}</span>
                </div>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="w-full h-10 bg-muted/20 border border-border/50 rounded-md focus:outline-none focus:ring-1 focus:ring-primary pl-8 pr-10 text-sm font-mono placeholder-muted-foreground transition-all"
                    placeholder="Inject scenario (e.g. 'scenario peak_load') or ask a question..."
                />
                <button
                    type="submit"
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground hover:text-primary transition-colors"
                >
                    <Send className="h-4 w-4" />
                </button>
            </div>
        </form>
    );
}
