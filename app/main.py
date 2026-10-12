import logging
import time
from collections.abc import Callable

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import llm
from app.config import get_settings

# Request logs carry metadata only (status, latency, question length).
# Never log the question or the answer (CLAUDE.md rule 8).
logger = logging.getLogger("docq")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

app = FastAPI(title="DocQ")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


def get_model_caller() -> Callable[[str], str]:
    """Dependency that returns the function answering a question.

    Tests replace this with a fake so the real model is never called.
    """
    settings = get_settings()
    return lambda question: llm.ask_model(question, settings)


@app.middleware("http")
async def log_request(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        latency_ms = round((time.perf_counter() - start) * 1000)
        question_len = getattr(request.state, "question_len", None)
        logger.info(
            "request method=%s path=%s status=%s latency_ms=%s question_len=%s",
            request.method,
            request.url.path,
            status,
            latency_ms,
            question_len,
        )


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # The default body repeats the user's input back; return a fixed message instead.
    return JSONResponse(status_code=422, content={"error": "invalid_request"})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "internal_error"})


@app.get("/")
def root() -> dict[str, str]:
    """Tells which version of the service answered (used to see revisions in Cloud Run)."""
    return {"service": "docq", "version": "v2"}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check: returns 200 if the app process is up and serving."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    request: Request,
    call_model: Callable[[str], str] = Depends(get_model_caller),
):
    question = body.question.strip()
    request.state.question_len = len(question)

    if not question:
        return JSONResponse(status_code=422, content={"error": "question_empty"})
    if len(question) > get_settings().max_question_chars:
        return JSONResponse(status_code=422, content={"error": "question_too_long"})

    try:
        answer = call_model(question)
    except llm.ModelTimeout:
        return JSONResponse(status_code=504, content={"error": "model_timeout"})
    except llm.ModelError:
        return JSONResponse(status_code=502, content={"error": "model_unavailable"})
    return AskResponse(answer=answer)
