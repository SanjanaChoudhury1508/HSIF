from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from backend.app.services.pipeline_service import PipelineService
from backend.app.schemas.process import (
    ProcessResponse,
    HumanStateTrajectoryResponse,
)
from database.repository import SessionRepository

router = APIRouter()

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

    content = await audio.read()

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

        result = pipeline_service.process_audio(temp_path)

        return result

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing failed: {exc}"
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