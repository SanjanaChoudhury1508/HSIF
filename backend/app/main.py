from fastapi import FastAPI

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