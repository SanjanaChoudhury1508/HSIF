
import json
import logging
import tempfile
import wave

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from backend.app.api.process import pipeline_service
from ai.speech.streaming.chunk_processor import StreamingAudioProcessor


router = APIRouter()
logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
MAX_AUDIO_BYTES = 10 * 1024 * 1024


async def send_event(websocket, event_type, session_id, **payload):
    await websocket.send_json({
        "type": event_type,
        "session_id": session_id,
        **payload
    })


@router.websocket("/ws/session/{session_id}")
async def stream_session(websocket: WebSocket, session_id: str):
    try:
        UUID(session_id)
    except ValueError:
        await websocket.close(code=1008, reason="session_id must be a UUID")
        return

    await websocket.accept()

    session_started = False
    audio_buffer = bytearray()
    processor = StreamingAudioProcessor(sample_rate=SAMPLE_RATE)
    chunk_index = 0

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if message.get("bytes") is not None:
                if not session_started:
                    await send_event(
                        websocket, "error", session_id,
                        code="SESSION_NOT_STARTED",
                        message="Send start_session before audio.",
                        recoverable=False
                    )
                    continue

                chunk = message["bytes"]

                if len(audio_buffer) + len(chunk) > MAX_AUDIO_BYTES:
                    audio_buffer.clear()
                    processor.reset()
                    chunk_index = 0
                    await send_event(
                        websocket, "error", session_id,
                        code="AUDIO_TOO_LARGE",
                        message="Turn exceeds the audio size limit.",
                        recoverable=True
                    )
                    continue

                try:
                    result = processor.process_chunk(chunk)
                except ValueError as exc:
                    await send_event(
                        websocket, "error", session_id,
                        code="INVALID_PCM",
                        message=str(exc),
                        recoverable=True
                    )
                    continue

                audio_buffer.extend(chunk)
                if chunk:
                    chunk_index += 1

                await send_event(
                    websocket, "speech_chunk", session_id,
                    chunk_index=chunk_index,
                    duration=result["duration"],
                    total_duration=result["total_duration"],
                    speech_duration=result["speech_duration"],
                    is_speech=result["is_speech"]
                )
                continue

            raw_text = message.get("text")
            if raw_text is None:
                continue

            try:
                control = json.loads(raw_text)
            except json.JSONDecodeError:
                await send_event(
                    websocket, "error", session_id,
                    code="INVALID_JSON",
                    message="Control message must be valid JSON.",
                    recoverable=True
                )
                continue

            if not isinstance(control, dict):
                await send_event(
                    websocket, "error", session_id,
                    code="INVALID_MESSAGE",
                    message="Control message must be a JSON object.",
                    recoverable=True
                )
                continue

            event_type = control.get("type")

            if event_type == "start_session":
                if session_started:
                    await send_event(
                        websocket, "error", session_id,
                        code="SESSION_ALREADY_STARTED",
                        message="This connection already has a session.",
                        recoverable=True
                    )
                    continue

                audio = control.get("audio", {})
                if not isinstance(audio, dict) or (
                    audio.get("encoding") != "pcm_s16le"
                    or audio.get("sample_rate") != SAMPLE_RATE
                    or audio.get("channels") != CHANNELS
                ):
                    await send_event(
                        websocket, "error", session_id,
                        code="INVALID_AUDIO_FORMAT",
                        message="Expected mono 16000 Hz pcm_s16le audio.",
                        recoverable=False
                    )
                    await websocket.close(code=1008)
                    return

                session_started = True
                await send_event(
                    websocket, "session_ready", session_id,
                    protocol_version=1,
                    audio={
                        "encoding": "pcm_s16le",
                        "sample_rate": SAMPLE_RATE,
                        "channels": CHANNELS
                    }
                )
                continue

            if not session_started:
                await send_event(
                    websocket, "error", session_id,
                    code="SESSION_NOT_STARTED",
                    message="Send start_session first.",
                    recoverable=True
                )
                continue

            if event_type == "end_turn":
                turn_id = control.get("turn_id")
                if not isinstance(turn_id, str) or not turn_id.strip():
                    await send_event(
                        websocket, "error", session_id,
                        code="INVALID_TURN_ID",
                        message="A non-empty turn_id is required.",
                        recoverable=True
                    )
                    continue

                if not audio_buffer:
                    await send_event(
                        websocket, "error", session_id,
                        code="EMPTY_TURN",
                        turn_id=turn_id,
                        message="No audio was received for this turn.",
                        recoverable=True
                    )
                    processor.reset()
                    chunk_index = 0
                    continue

                if len(audio_buffer) % SAMPLE_WIDTH_BYTES:
                    await send_event(
                        websocket, "error", session_id,
                        code="INVALID_PCM_LENGTH",
                        turn_id=turn_id,
                        message="Audio ended in the middle of a PCM sample.",
                        recoverable=True
                    )
                    audio_buffer.clear()
                    processor.reset()
                    chunk_index = 0
                    continue

                pcm_bytes = bytes(audio_buffer)
                audio_buffer.clear()

                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False
                    ) as temp_file:
                        temp_path = Path(temp_file.name)

                    with wave.open(str(temp_path), "wb") as wav_file:
                        wav_file.setnchannels(CHANNELS)
                        wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
                        wav_file.setframerate(SAMPLE_RATE)
                        wav_file.writeframes(pcm_bytes)

                    result = await run_in_threadpool(
                        pipeline_service.process_audio, temp_path
                    )

                    await send_event(
                        websocket, "transcript_final", session_id,
                        turn_id=turn_id,
                        text=result["speech"]["transcript"]
                    )
                    await send_event(
                        websocket, "human_state_update", session_id,
                        turn_id=turn_id,
                        state=result["human_state"],
                        final=True
                    )

                    dialogue = result["dialogue"]
                    policy = dialogue.get("policy", {})

                    await send_event(
                        websocket, "dialogue_strategy", session_id,
                        turn_id=turn_id,
                        strategy=policy.get("strategy"),
                        reason=policy.get("reason")
                    )
                    await send_event(
                        websocket, "assistant_response", session_id,
                        turn_id=turn_id,
                        text=result["response"],
                        strategy=policy.get("strategy")
                    )

                except Exception:
                    logger.exception("Streaming turn failed")
                    await send_event(
                        websocket, "error", session_id,
                        turn_id=turn_id,
                        code="PIPELINE_FAILED",
                        message="The turn could not be processed.",
                        recoverable=True
                    )
                finally:
                    if temp_path is not None:
                        temp_path.unlink(missing_ok=True)
                    processor.reset()
                    chunk_index = 0

                continue

            if event_type == "end_session":
                audio_buffer.clear()
                await send_event(websocket, "session_ended", session_id)
                await websocket.close(code=1000)
                return

            if event_type == "ping":
                await send_event(websocket, "pong", session_id)
                continue

            await send_event(
                websocket, "error", session_id,
                code="UNKNOWN_EVENT",
                message=f"Unsupported event type: {event_type}",
                recoverable=True
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception:
        logger.exception("Unexpected streaming error: %s", session_id)
