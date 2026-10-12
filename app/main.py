from fastapi import FastAPI

app = FastAPI(title="DocQ")


@app.get("/")
def root() -> dict[str, str]:
    """Tells which version of the service answered (used to see revisions in Cloud Run)."""
    return {"service": "docq", "version": "v2"}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check: returns 200 if the app process is up and serving."""
    return {"status": "ok"}
