import asyncio
import json
import uuid
import wave
from pathlib import Path

import websockets

async def recv(ws, timeout=30):
    return json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))

async def main():
    with wave.open("tests/audio/processed.wav", "rb") as wav:
        pcm = wav.readframes(wav.getnframes())

    uri = f"ws://127.0.0.1:8000/ws/session/{uuid.uuid4()}"

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "type": "start_session",
            "audio": {
                "encoding": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1
            }
        }))
        print("Session:", await recv(ws))

        await ws.send("{invalid json")
        print("Expected error:", await recv(ws))

        await ws.send(pcm[:8000])
        recovered = await recv(ws)
        print("After invalid JSON:", recovered)

        assert recovered.get("type") == "speech_chunk", (
            "Connection did not recover after malformed JSON"
        )
        assert recovered.get("chunk_index") == 1
        assert recovered.get("start") == 0.0

        print("PASS: same connection recovered after invalid JSON")

asyncio.run(main())
