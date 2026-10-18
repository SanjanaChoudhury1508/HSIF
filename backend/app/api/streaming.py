
import asyncio
import json
import logging
import tempfile
import wave

from pathlib import Path
from uuid import UUID
from time import perf_counter

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from backend.app.api.process import get_pipeline_service

router = APIRouter()
logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB per turn


async def send_event(
    websocket: WebSocket,
    event_type: str,
    session_id: str,
    **payload,
):
    await websocket.send_json(
        {
            "type": event_type,
            "session_id": session_id,
            **payload,
        }
    )


@router.websocket("/ws/session/{session_id}")
async def stream_session(
    websocket: WebSocket,
    session_id: str,
):
    # Validate the session identifier before processing audio.
    try:
        UUID(session_id)
    except ValueError:
        await websocket.close(
            code=1008,
            reason="session_id must be a UUID",
        )
        return

    await websocket.accept()

    session_started = False
    turn_id = None
    audio_buffer = bytearray()

    try:
        while True:
            message = await websocket.receive()

            # Handle disconnect frames.
            if message.get("type") == "websocket.disconnect":
                break

            # Binary frames contain raw PCM audio.
            if message.get("bytes") is not None:
                if not session_started:
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        code="SESSION_NOT_STARTED",
                        message="Send start_session before audio.",
                        recoverable=False,
                    )
                    continue

                chunk = message["bytes"]

                if len(audio_buffer) + len(chunk) > MAX_AUDIO_BYTES:
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        turn_id=turn_id,
                        code="AUDIO_TOO_LARGE",
                        message="Turn exceeds the audio size limit.",
                        recoverable=True,
                    )
                    audio_buffer.clear()
                    turn_id = None
                    continue

                audio_buffer.extend(chunk)
                continue

            # All control messages must be JSON objects.
            raw_text = message.get("text")
            if raw_text is None:
                continue

            try:
                control = json.loads(raw_text)
            except json.JSONDecodeError:
                await send_event(
                    websocket,
                    "error",
                    session_id,
                    code="INVALID_JSON",
                    message="Control message must be valid JSON.",
                    recoverable=True,
                )
                continue

            if not isinstance(control, dict):
                await send_event(
                    websocket,
                    "error",
                    session_id,
                    code="INVALID_MESSAGE",
                    message="Control message must be a JSON object.",
                    recoverable=True,
                )
                continue

            event_type = control.get("type")

            # Initialize the audio session.
            if event_type == "start_session":
                if session_started:
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        code="SESSION_ALREADY_STARTED",
                        message="This connection already has a session.",
                        recoverable=True,
                    )
                    continue

                audio = control.get("audio", {})

                if (
                    audio.get("encoding") != "pcm_s16le"
                    or audio.get("sample_rate") != SAMPLE_RATE
                    or audio.get("channels") != CHANNELS
                ):
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        code="INVALID_AUDIO_FORMAT",
                        message=(
                            "Expected mono 16000 Hz pcm_s16le audio."
                        ),
                        recoverable=False,
                    )
                    await websocket.close(code=1008)
                    return

                try:
                    # Initialize the existing pipeline and persistence.
                    # This may require GEMINI_API_KEY in your environment.
                    await run_in_threadpool(
                        get_pipeline_service,
                        session_id,
                    )
                except Exception:
                    logger.exception("Could not initialize HSIF session")
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        code="SESSION_INITIALIZATION_FAILED",
                        message="Could not initialize the HSIF session.",
                        recoverable=False,
                    )
                    await websocket.close(code=1011)
                    return

                session_started = True

                await send_event(
                    websocket,
                    "session_ready",
                    session_id,
                    protocol_version=1,
                    audio={
                        "encoding": "pcm_s16le",
                        "sample_rate": SAMPLE_RATE,
                        "channels": CHANNELS,
                    },
                )
                continue

            if not session_started:
                await send_event(
                    websocket,
                    "error",
                    session_id,
                    code="SESSION_NOT_STARTED",
                    message="Send start_session first.",
                    recoverable=True,
                )
                continue

            # End the current spoken turn and run the existing pipeline.
            if event_type == "end_turn":
                requested_turn_id = control.get("turn_id")

                if (
                    not isinstance(requested_turn_id, str)
                    or not requested_turn_id.strip()
                    or len(requested_turn_id) > 100
                ):
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        code="INVALID_TURN_ID",
                        message="A non-empty turn_id is required.",
                        recoverable=True,
                    )
                    continue

                if not audio_buffer:
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        turn_id=requested_turn_id,
                        code="EMPTY_TURN",
                        message="No audio was received for this turn.",
                        recoverable=True,
                    )
                    continue

                # PCM frames must contain whole 16-bit samples.
                if len(audio_buffer) % SAMPLE_WIDTH_BYTES != 0:
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        turn_id=requested_turn_id,
                        code="INVALID_PCM_LENGTH",
                        message="Audio ended in the middle of a PCM sample.",
                        recoverable=True,
                    )
                    audio_buffer.clear()
                    continue

                turn_id = requested_turn_id
                pcm_bytes = bytes(audio_buffer)
                audio_buffer.clear()

                started_at = perf_counter()

                try:
                    # Create a WAV file that the existing SpeechService
                    # can read through PipelineService.process_audio().
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav",
                        delete=False,
                    ) as temp_file:
                        wav_path = Path(temp_file.name)

                    try:
                        with wave.open(str(wav_path), "wb") as wav_file:
                            wav_file.setnchannels(CHANNELS)
                            wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
                            wav_file.setframerate(SAMPLE_RATE)
                            wav_file.writeframes(pcm_bytes)

                        pipeline = await run_in_threadpool(
                            get_pipeline_service,
                            session_id,
                        )

                        result = await run_in_threadpool(
                            pipeline.process_audio,
                            str(wav_path),
                        )
                    finally:
                        wav_path.unlink(missing_ok=True)

                    transcript = result["speech"]["transcript"]
                    human_state = result["human_state"]
                    dialogue = result["dialogue"]
                    policy = dialogue.get("policy", {})

                    await send_event(
                        websocket,
                        "transcript_final",
                        session_id,
                        turn_id=turn_id,
                        text=transcript,
                    )

                    await send_event(
                        websocket,
                        "human_state_update",
                        session_id,
                        turn_id=turn_id,
                        state=human_state,
                        final=True,
                    )

                    await send_event(
                        websocket,
                        "dialogue_strategy",
                        session_id,
                        turn_id=turn_id,
                        strategy=policy.get("strategy"),
                        reason=policy.get("reason"),
                    )

                    await send_event(
                        websocket,
                        "assistant_response",
                        session_id,
                        turn_id=turn_id,
                        text=result["response"],
                        strategy=policy.get("strategy"),
                        latency_ms=round(
                            (perf_counter() - started_at) * 1000
                        ),
                    )

                except Exception:
                    logger.exception(
                        "HSIF turn processing failed: %s",
                        turn_id,
                    )
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        turn_id=turn_id,
                        code="PIPELINE_FAILED",
                        message="The turn could not be processed.",
                        recoverable=True,
                    )
                finally:
                    turn_id = None

                continue

            if event_type == "end_session":
                audio_buffer.clear()

                await send_event(
                    websocket,
                    "session_ended",
                    session_id,
                )

                await websocket.close(code=1000)
                return

            if event_type == "ping":
                await send_event(
                    websocket,
                    "pong",
                    session_id,
                )
                continue

            await send_event(
                websocket,
                "error",
                session_id,
                code="UNKNOWN_EVENT",
                message=f"Unsupported event type: {event_type}",
                recoverable=True,
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)

    except Exception:
        logger.exception("Unexpected streaming error: %s", session_id)

        try:
            await send_event(
                websocket,
                "error",
                session_id,
                code="INTERNAL_ERROR",
                message="Unexpected streaming server error.",
                recoverable=False,
            )
        except Exception:
            pass
