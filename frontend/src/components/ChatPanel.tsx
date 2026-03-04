/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User } from 'lucide-react';
import useWebSocket from 'react-use-websocket';
import { wsUrl } from '@/lib/config';

interface ChatPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

interface DisplayMessage {
    role: 'user' | 'assistant';
    content: string;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ isOpen, onClose }) => {
    const [messages, setMessages] = useState<DisplayMessage[]>([]);
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const { sendMessage } = useWebSocket(wsUrl('/ws/commands'), {
        shouldReconnect: () => true,
        onMessage: (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'agent_message' || data.type === 'system') {
                    setMessages(prev => [...prev, { role: 'assistant', content: data.content || data.message }]);
                }
            } catch (e) {
                console.error('Failed to parse WS message', e);
            }
        }
    });

    useEffect(() => {
        if (isOpen) {
            inputRef.current?.focus();
        }
    }, [isOpen]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = () => {
        const trimmed = input.trim();
        if (!trimmed) return;

        setMessages(prev => [...prev, { role: 'user', content: trimmed }]);

        // Parse commands for scenario injection
        let action = "nl_query";
        let payload = trimmed;

        if (trimmed.startsWith("scenario ")) {
            action = "trigger_scenario";
            payload = trimmed.replace("scenario ", "");
        } else if (trimmed.toLowerCase() === "rollback") {
            action = "rollback";
            payload = "";
        }

        sendMessage(JSON.stringify({ action, payload }));
        setInput('');
    };

    if (!isOpen) return null;

    return (
        <div className="flex flex-col h-full bg-[#050507]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e24] flex-none">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-emerald-500/20 border border-emerald-500/40 rounded flex items-center justify-center">
                        <Bot className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <div>
                        <span className="text-xs font-bold text-white tracking-wider">AI ORCHESTRATOR</span>
                        <span className="ml-2 text-[9px] text-emerald-500 font-mono">LINK STABLE</span>
                    </div>
                </div>
                <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 transition-colors">
                    <X className="w-4 h-4" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                    <div className="text-center py-8">
                        <Bot className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
                        <p className="text-[10px] text-zinc-600 font-mono uppercase tracking-widest mb-2">Commlink Established</p>
                        <p className="text-xs text-zinc-500">Inject scenarios (e.g. "scenario overload") or talk to the Agent.</p>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role === 'assistant' && (
                            <div className="w-5 h-5 mt-0.5 bg-emerald-500/20 border border-emerald-500/40 rounded flex items-center justify-center flex-shrink-0">
                                <Bot className="w-3 h-3 text-emerald-400" />
                            </div>
                        )}
                        <div className={`max-w-[80%] px-3 py-2 rounded-lg text-xs font-mono leading-relaxed whitespace-pre-wrap
              ${msg.role === 'user'
                                ? 'bg-blue-500/10 border border-blue-500/20 text-blue-200'
                                : 'bg-[#111116] border border-[#1e1e24] text-zinc-300'}`}>
                            {msg.content}
                        </div>
                        {msg.role === 'user' && (
                            <div className="w-5 h-5 mt-0.5 bg-blue-500/20 border border-blue-500/40 rounded flex items-center justify-center flex-shrink-0">
                                <User className="w-3 h-3 text-blue-400" />
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <div className="p-3 border-t border-[#1e1e24] flex-none">
                <div className="flex items-center gap-2 bg-[#111116] border border-[#1e1e24] rounded-lg px-3 py-2">
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                        placeholder="scenario peak_load, rollback, or message..."
                        className="flex-1 bg-transparent text-xs text-zinc-200 font-mono placeholder-zinc-600 outline-none"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim()}
                        className="text-emerald-400 hover:text-emerald-300 disabled:text-zinc-700 transition-colors"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
};
