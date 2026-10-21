import asyncio
import json
import time
import uuid
import wave
from pathlib import Path

import websockets

HOST = "ws://127.0.0.1:8000"
AUDIO_PATH = Path("tests/audio/processed.wav")
CHUNK_MS = 250

async def main():
    session_id = str(uuid.uuid4())
    uri = f"{HOST}/ws/session/{session_id}"

    with wave.open(str(AUDIO_PATH), "rb") as wav:
        assert wav.getframerate() == 16000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        pcm = wav.readframes(wav.getnframes())

    chunk_size = 16000 * 2 * CHUNK_MS // 1000
    events = []
    started = time.perf_counter()

    async with websockets.connect(uri, open_timeout=30) as ws:
        await ws.send(json.dumps({
            "type": "start_session",
            "audio": {
                "encoding": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1
            }
        }))

        ready = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
        events.append(ready)
        print("SESSION:", ready)

        if ready.get("type") != "session_ready":
            print("Session did not become ready; stopping test.")
            return

        # Send timed chunks and collect responses as they arrive.
        for offset in range(0, len(pcm), chunk_size):
            chunk = pcm[offset:offset + chunk_size]
            await ws.send(chunk)

            # Drain currently available events without waiting for the next one.
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.03)
                    event = json.loads(raw)
                    events.append(event)
                    print(f"{time.perf_counter()-started:7.3f}s", event)
                except asyncio.TimeoutError:
                    break

            await asyncio.sleep(CHUNK_MS / 1000)

        await ws.send(json.dumps({
            "type": "end_turn",
            "turn_id": "live-check-1"
        }))

        # Wait for final events; the speech models may take a while.
        deadline = time.perf_counter() + 180
        while time.perf_counter() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                event = json.loads(raw)
                events.append(event)
                print(f"{time.perf_counter()-started:7.3f}s", event)
                if event.get("type") == "assistant_response":
                    break
                if event.get("type") == "error" and event.get("code") == "PIPELINE_FAILED":
                    break
            except asyncio.TimeoutError:
                print("Still waiting for pipeline response...")
        else:
            print("Timed out waiting for final pipeline events.")

    print("\nEVENT SUMMARY")
    for event_type in sorted({e.get("type", "unknown") for e in events}):
        matching = [e for e in events if e.get("type") == event_type]
        print(f"{event_type}: {len(matching)}")

    print("\nFINAL EVENT CHECK")
    expected = [
        "speech_chunk",
        "transcript_partial",
        "transcript_final",
        "human_state_update",
        "dialogue_strategy",
        "assistant_response",
    ]
    for name in expected:
        print(f"{name}: {'PASS' if any(e.get('type') == name for e in events) else 'NOT OBSERVED'}")

asyncio.run(main())
