/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

const DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions';

const SYSTEM_PROMPT = `You are an AI mission analyst embedded in the G-TT&C (Global Tracking, Telemetry & Command) Mission Control dashboard. You have access to real-time data about a network of surveillance and communications nodes spread across Europe.

The network consists of four segments:
- DOMESTIC: Core Western European ground stations (London, Paris, Berlin, Brussels, Amsterdam, Frankfurt, Munich, Rome)
- OVERSEAS: Extended reach posts (Madrid, Warsaw, Bucharest, Stockholm, Athens, Istanbul)
- MARITIME: Sea corridor patrol vessels and buoys (North Sea, Mediterranean, Baltic, English Channel, Adriatic, Norwegian Sea)
- SPACE: Geostationary satellites, polar relays, and ground uplink stations (Azores, Svalbard)

You help operators by:
- Analyzing node status, telemetry anomalies, and coverage gaps
- Recommending tactical responses to outages or surges
- Explaining network topology and segment health
- Providing situational awareness briefs

Keep responses concise, tactical, and use military/intelligence-style brevity where appropriate. Reference specific node IDs and segment names when discussing the network.`;

export async function chatWithDeepSeek(messages: ChatMessage[]): Promise<string> {
  const apiKey = process.env.DEEPSEEK_API_KEY;

  if (!apiKey) {
    return '[COMMS OFFLINE] DeepSeek API key not configured. Set DEEPSEEK_API_KEY in environment to enable AI analyst.';
  }

  const fullMessages: ChatMessage[] = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...messages,
  ];

  const response = await fetch(DEEPSEEK_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: fullMessages,
      temperature: 0.7,
      max_tokens: 1024,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`DeepSeek API error (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  return data.choices?.[0]?.message?.content ?? '[No response from analyst]';
}
