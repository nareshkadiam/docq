from fastapi import FastAPI

app = FastAPI(title="DocQ")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check: returns 200 if the app process is up and serving."""
    return {"status": "ok"}
