import asyncio
import json
import uuid

import websockets

BASE = "ws://127.0.0.1:8000/ws/session/"

async def event(ws, timeout=30):
    return json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))

async def start(ws):
    await ws.send(json.dumps({
        "type": "start_session",
        "audio": {
            "encoding": "pcm_s16le",
            "sample_rate": 16000,
            "channels": 1
        }
    }))
    return await event(ws)

async def main():
    # Test 1: binary audio before starting a session.
    async with websockets.connect(BASE + str(uuid.uuid4())) as ws:
        await ws.send(b"\x00\x00")
        result = await event(ws)
        print("Audio before start:", result)

    # Test 2: odd-length PCM should be rejected.
    async with websockets.connect(BASE + str(uuid.uuid4())) as ws:
        print("Start:", await start(ws))
        await ws.send(b"\x00")  # Invalid: 16-bit PCM needs even byte length.
        result = await event(ws)
        print("Odd PCM:", result)

    # Test 3: empty turn should be rejected without crashing the session.
    async with websockets.connect(BASE + str(uuid.uuid4())) as ws:
        print("Start:", await start(ws))
        await ws.send(json.dumps({
            "type": "end_turn",
            "turn_id": "empty-turn-check"
        }))
        result = await event(ws)
        print("Empty turn:", result)

    # Test 4: malformed JSON/control message.
    async with websockets.connect(BASE + str(uuid.uuid4())) as ws:
        print("Start:", await start(ws))
        await ws.send("{not valid json")
        try:
            print("Malformed control:", await event(ws))
        except websockets.ConnectionClosed as exc:
            print("Connection closed:", exc.code, exc.reason)

asyncio.run(main())
