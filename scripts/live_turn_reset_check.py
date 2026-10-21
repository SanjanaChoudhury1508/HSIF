import asyncio
import json
import uuid
import wave
from pathlib import Path

import websockets

URI = f"ws://127.0.0.1:8000/ws/session/{uuid.uuid4()}"
AUDIO = Path("tests/audio/processed.wav")
CHUNK_SIZE = 8000  # 250 ms of 16 kHz, mono, 16-bit PCM

async def receive_event(ws, timeout=120):
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)

async def main():
    with wave.open(str(AUDIO), "rb") as wav:
        pcm = wav.readframes(wav.getnframes())

    async with websockets.connect(URI, open_timeout=30) as ws:
        await ws.send(json.dumps({
            "type": "start_session",
            "audio": {
                "encoding": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1
            }
        }))
        ready = await receive_event(ws)
        assert ready["type"] == "session_ready", ready

        for turn_number in (1, 2):
            first_chunk = True
            for offset in range(0, len(pcm), CHUNK_SIZE):
                await ws.send(pcm[offset:offset + CHUNK_SIZE])

                # The server emits one speech_chunk per audio chunk.
                while True:
                    event = await receive_event(ws)
                    if event["type"] == "speech_chunk":
                        if first_chunk:
                            print(
                                f"TURN {turn_number}: "
                                f"first chunk index={event['chunk_index']}, "
                                f"start={event['start']}, "
                                f"end={event['end']}"
                            )
                            assert event["chunk_index"] == 1
                            assert event["start"] == 0.0
                            first_chunk = False
                        break
                    elif event["type"] == "error":
                        raise AssertionError(event)

            await ws.send(json.dumps({
                "type": "end_turn",
                "turn_id": f"reset-check-{turn_number}"
            }))

            received = []
            while True:
                event = await receive_event(ws, timeout=180)
                received.append(event)
                if event["type"] == "assistant_response":
                    break
                if event["type"] == "error" and event.get("code") == "PIPELINE_FAILED":
                    raise AssertionError(event)

            final = next(
                e for e in received if e["type"] == "transcript_final"
            )
            print(f"TURN {turn_number}: final transcript={final['text']!r}")
            assert final["turn_id"] == f"reset-check-{turn_number}"

        await ws.send(json.dumps({"type": "end_session"}))
        ended = await receive_event(ws)
        assert ended["type"] == "session_ended", ended
        print("PASS: consecutive turns and session cleanup")

asyncio.run(main())
