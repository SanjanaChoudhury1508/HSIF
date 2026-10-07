from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.process import router as process_router

app = FastAPI(
    title="HSIF Backend",
    description="Human State Intelligence Framework API",
    version="1.0.0",
)

# Allow the local frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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