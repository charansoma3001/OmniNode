import asyncio
import websockets
import json

async def trigger():
    async with websockets.connect("ws://localhost:8000/ws/commands") as ws:
        # 1. Trigger the malicious command in real mode
        await ws.send(json.dumps({
            "action": "trigger_scenario",
            "payload": "cyber_attack"
        }))
        print("Sent cyber_attack scenario trigger.")
        
if __name__ == "__main__":
    asyncio.run(trigger())
