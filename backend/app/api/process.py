from pathlib import Path
from tempfile import NamedTemporaryFile
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from backend.app.services.pipeline_service import PipelineService
from backend.app.services.llm.gemini_provider import GeminiQuotaExceededError
from backend.app.schemas.process import (
    ProcessResponse,
    HumanStateTrajectoryResponse,
)
from database.repository import SessionRepository

router = APIRouter()
logger = logging.getLogger(__name__)

class TextMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)

# In-memory session store.
# Each session gets its own PipelineService and conversation memory.
sessions: dict[str, PipelineService] = {}
repository = SessionRepository()

ALLOWED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".flac",
    ".aac",
}

MAX_FILE_SIZE = 25 * 1024 * 1024


def get_pipeline_service(
    session_id: str,
    llm_provider=None,
) -> PipelineService:
    if session_id not in sessions:
        sessions[session_id] = PipelineService(
            session_id=session_id,
            repository=repository,
            llm_provider=llm_provider,
        )

    return sessions[session_id]


@router.post(
    "/process",
    response_model=ProcessResponse
)
async def process_audio(
    audio: UploadFile = File(...),
    session_id: str = Query(
        ...,
        min_length=1,
        description="Unique identifier for the conversation session."
    ),
):
    if not audio.filename:
        raise HTTPException(
            status_code=400,
            detail="Audio file is required."
        )

    extension = Path(audio.filename).suffix.lower()

    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported audio format: {extension}. "
                f"Supported formats: "
                f"{', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
            )
        )

    content = await audio.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded audio file is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Audio file exceeds the 25 MB size limit."
        )

    temp_path = None

    try:
        with NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        pipeline_service = get_pipeline_service(session_id)

        result = await run_in_threadpool(
            pipeline_service.process_audio,
            temp_path,
        )

        return result

    except FileNotFoundError:
        logger.exception("Uploaded audio processing failed because a file was missing")
        raise HTTPException(
            status_code=404,
            detail="Audio file could not be processed."
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except GeminiQuotaExceededError:
        logger.warning("Audio processing stopped because Gemini quota is exhausted")
        raise HTTPException(
            status_code=429,
            detail="Gemini quota is exhausted. Please try again later.",
        )

    except TimeoutError:
        logger.warning("Audio processing timed out")
        raise HTTPException(
            status_code=504,
            detail="Audio processing timed out. Please try again.",
        )

    except Exception:
        logger.exception("Unexpected audio processing failure")
        raise HTTPException(
            status_code=500,
            detail="Audio processing failed. Please try again."
        )

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
            
@router.get(
    "/session/{session_id}/state",
    response_model=HumanStateTrajectoryResponse,
)
async def get_session_state(session_id: str):
    pipeline_service = get_pipeline_service(session_id)

    current_state = pipeline_service.human_state_engine.get_current_state()

    return {
        "session_id": session_id,
        "current_state": (
            current_state.to_dict()
            if current_state is not None
            else None
        ),
        "trajectory": (
            pipeline_service.human_state_engine.get_state_trajectory()
        ),
        "changes": (
            pipeline_service.human_state_engine.get_state_changes()
        ),
    }

@router.post("/message")
async def process_text_message(
    payload: TextMessageRequest,
    session_id: str = Query(
        ...,
        min_length=1,
        description="Unique identifier for the conversation session.",
    ),
):
    message = payload.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        pipeline_service = get_pipeline_service(session_id)
        return pipeline_service.process_text(message)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        logger.exception("Unexpected text processing failure")
        raise HTTPException(
            status_code=500,
            detail="Text processing failed. Please try again.",
        )

@router.get("/sessions")
def list_sessions():
    return {
        "sessions": repository.list_sessions()
    }


@router.get("/sessions/{session_id}")
def get_session_history(session_id: str):
    history = repository.get_session_history(session_id)

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return history
