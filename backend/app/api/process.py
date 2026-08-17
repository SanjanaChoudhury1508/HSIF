from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.app.services.pipeline_service import PipelineService


router = APIRouter()

pipeline_service = PipelineService()


@router.post("/process")
async def process_audio(
    audio: UploadFile = File(...)
):
    if not audio.filename:
        raise HTTPException(
            status_code=400,
            detail="Audio file is required."
        )

    suffix = Path(audio.filename).suffix

    try:
        with NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            content = await audio.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        result = pipeline_service.process_audio(temp_path)

        return result

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing failed: {exc}"
        )

    finally:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink(missing_ok=True)