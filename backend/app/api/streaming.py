
import json
import logging
import tempfile
import wave
from pathlib import Path
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from backend.app.api.process import get_pipeline_service
from ai.speech.streaming.chunk_processor import StreamingAudioProcessor


router = APIRouter()
logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
MAX_AUDIO_BYTES = 10 * 1024 * 1024

PARTIAL_TRANSCRIPTION_INTERVAL_SECONDS = 1.5
MIN_PARTIAL_AUDIO_SECONDS = 1.0


async def send_event(websocket, event_type, session_id, **payload):
    await websocket.send_json({
        "type": event_type,
        "session_id": session_id,
        **payload,
    })


def reset_turn_state(
    audio_buffer,
    partial_audio_buffer,
    processor,
):
    """Clear audio and streaming state for the current turn."""
    audio_buffer.clear()
    partial_audio_buffer.clear()
    processor.reset()


@router.websocket("/ws/session/{session_id}")
async def stream_session(websocket: WebSocket, session_id: str):
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

    # Complete turn audio, used by the existing final pipeline.
    audio_buffer = bytearray()

    # Separate buffer used for interim transcription.
    partial_audio_buffer = bytearray()
    last_partial_duration = 0.0
    last_partial_text = ""

    processor = StreamingAudioProcessor(
        sample_rate=SAMPLE_RATE,
    )

    chunk_index = 0
    turn_id = None

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # ---------------------------------------------------------
            # Binary audio messages
            # ---------------------------------------------------------
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
                    reset_turn_state(
                        audio_buffer,
                        partial_audio_buffer,
                        processor,
                    )
                    chunk_index = 0
                    turn_id = None
                    last_partial_duration = 0.0
                    last_partial_text = ""

                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        code="AUDIO_TOO_LARGE",
                        message="Turn exceeds the audio size limit.",
                        recoverable=True,
                    )
                    continue

                try:
                    result = processor.process_chunk(chunk)
                except ValueError as exc:
                    reset_turn_state(
                        audio_buffer,
                        partial_audio_buffer,
                        processor,
                    )
                    chunk_index = 0
                    turn_id = None
                    last_partial_duration = 0.0
                    last_partial_text = ""

                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        code="INVALID_PCM",
                        message=str(exc),
                        recoverable=True,
                    )
                    continue

                audio_buffer.extend(chunk)

                if chunk:
                    partial_audio_buffer.extend(chunk)
                    chunk_index += 1

                # Publish chunk-level speech and acoustic metadata.
                await send_event(
                    websocket,
                    "speech_chunk",
                    session_id,
                    chunk_index=chunk_index,
                    duration=result["duration"],
                    total_duration=result["total_duration"],
                    speech_duration=result["speech_duration"],
                    is_speech=result["is_speech"],
                    start=result["start"],
                    end=result["end"],
                    energy=result["energy"],
                    speech_event=result["speech_event"],
                    pause=result["pause"],
                    pause_count=result["pause_count"],
                )

                # Generate interim transcripts periodically.
                if chunk:
                    current_duration = (
                        len(partial_audio_buffer)
                        / (
                            SAMPLE_RATE
                            * CHANNELS
                            * SAMPLE_WIDTH_BYTES
                        )
                    )

                    should_transcribe = (
                        current_duration
                        >= MIN_PARTIAL_AUDIO_SECONDS
                        and (
                            current_duration - last_partial_duration
                            >= PARTIAL_TRANSCRIPTION_INTERVAL_SECONDS
                        )
                    )

                    if should_transcribe:
                        # Update before calling Whisper to avoid
                        # repeatedly retrying the same audio duration.
                        last_partial_duration = current_duration

                        try:
                            pipeline = await run_in_threadpool(
                                get_pipeline_service,
                                session_id,
                            )

                            partial_text = await run_in_threadpool(
                                pipeline.speech_service.transcriber
                                .transcribe_pcm_chunk,
                                bytes(partial_audio_buffer),
                                SAMPLE_RATE,
                            )

                            partial_text = (
                                partial_text.strip()
                                if partial_text
                                else ""
                            )

                            if (
                                partial_text
                                and partial_text != last_partial_text
                            ):
                                await send_event(
                                    websocket,
                                    "transcript_partial",
                                    session_id,
                                    text=partial_text,
                                    start=0.0,
                                    end=current_duration,
                                    is_final=False,
                                )
                                last_partial_text = partial_text

                        except Exception:
                            # Interim transcription must not prevent
                            # the final turn pipeline from running.
                            logger.exception(
                                "Partial transcription failed "
                                "for session %s",
                                session_id,
                            )

                continue

            # ---------------------------------------------------------
            # JSON control messages
            # ---------------------------------------------------------
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

            # ---------------------------------------------------------
            # Start session
            # ---------------------------------------------------------
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

                if not isinstance(audio, dict) or (
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
                    await run_in_threadpool(
                        get_pipeline_service,
                        session_id,
                    )
                except Exception:
                    logger.exception(
                        "Could not initialize HSIF session"
                    )
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

            # ---------------------------------------------------------
            # End turn: run the complete existing pipeline
            # ---------------------------------------------------------
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

                    reset_turn_state(
                        audio_buffer,
                        partial_audio_buffer,
                        processor,
                    )
                    chunk_index = 0
                    last_partial_duration = 0.0
                    last_partial_text = ""
                    continue

                if len(audio_buffer) % SAMPLE_WIDTH_BYTES != 0:
                    await send_event(
                        websocket,
                        "error",
                        session_id,
                        turn_id=requested_turn_id,
                        code="INVALID_PCM_LENGTH",
                        message=(
                            "Audio ended in the middle of a PCM sample."
                        ),
                        recoverable=True,
                    )

                    reset_turn_state(
                        audio_buffer,
                        partial_audio_buffer,
                        processor,
                    )
                    chunk_index = 0
                    last_partial_duration = 0.0
                    last_partial_text = ""
                    continue

                turn_id = requested_turn_id
                pcm_bytes = bytes(audio_buffer)
                audio_buffer.clear()

                started_at = perf_counter()
                wav_path = None

                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav",
                        delete=False,
                    ) as temp_file:
                        wav_path = Path(temp_file.name)

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

                    dialogue = result["dialogue"]
                    policy = dialogue.get("policy", {})
                    speech = result["speech"]
                    await send_event(
                        websocket,
                        "transcript_final",
                        session_id,
                        turn_id=turn_id,
                        text=speech["transcript"],
                        is_final=True,
                        language=speech["language"],
                        language_probability=speech["language_probability"],
                        audio=speech["audio"],
                        vad=speech["vad"],
                        features=speech["features"],
                    )

                    await send_event(
                        websocket,
                        "human_state_update",
                        session_id,
                        turn_id=turn_id,
                        state=result["human_state"],
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
                    if wav_path is not None:
                        wav_path.unlink(missing_ok=True)

                    reset_turn_state(
                        audio_buffer,
                        partial_audio_buffer,
                        processor,
                    )
                    chunk_index = 0
                    turn_id = None
                    last_partial_duration = 0.0
                    last_partial_text = ""

                continue

            # ---------------------------------------------------------
            # End session
            # ---------------------------------------------------------
            if event_type == "end_session":
                reset_turn_state(
                    audio_buffer,
                    partial_audio_buffer,
                    processor,
                )
                chunk_index = 0
                last_partial_duration = 0.0
                last_partial_text = ""

                await send_event(
                    websocket,
                    "session_ended",
                    session_id,
                )
                await websocket.close(code=1000)
                return

            # ---------------------------------------------------------
            # Ping / pong
            # ---------------------------------------------------------
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
        logger.exception(
            "Unexpected streaming error: %s",
            session_id,
        )

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

    finally:
        reset_turn_state(
            audio_buffer,
            partial_audio_buffer,
            processor,
        )