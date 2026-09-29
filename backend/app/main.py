from fastapi import FastAPI
from backend.app.api.process import router as process_router

app = FastAPI(
    title="HSIF Backend",
    description="Human State Intelligence Framework API",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "HSIF Backend"
    }

app.include_router(
    process_router,
    prefix="/api/v1"
)