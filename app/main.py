import os
import time
from collections.abc import Callable

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import llm, logs
from app.config import get_settings

# Request logs carry metadata only (status, latency, question length, error code).
# Never log the question, the answer or an exception message (CLAUDE.md rule 8).
logger = logs.get_logger()

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


def error_response(request: Request, status_code: int, code: str) -> JSONResponse:
    """Fixed-message error body; the code is also recorded for the request log."""
    request.state.error = code
    return JSONResponse(status_code=status_code, content={"error": code})


@app.middleware("http")
async def log_request(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    except Exception as exc:
        # The handler that builds the 500 runs after this middleware, so record it here.
        # Class name only: the message can repeat the user's input.
        request.state.error = "internal_error"
        request.state.exception_type = type(exc).__name__
        raise
    finally:
        fields = {
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "latency_ms": round((time.perf_counter() - start) * 1000),
        }
        # Read the project straight from the environment: logging must never fail
        # because of an unrelated (bad) setting.
        trace = logs.trace_from_header(
            request.headers.get("x-cloud-trace-context"), os.getenv("GOOGLE_CLOUD_PROJECT")
        )
        optional = {
            "question_len": getattr(request.state, "question_len", None),
            "error": getattr(request.state, "error", None),
            "exception_type": getattr(request.state, "exception_type", None),
            logs.TRACE_KEY: trace,
        }
        fields.update({key: value for key, value in optional.items() if value is not None})
        logger.log(logs.level_for(status), "request", extra={"fields": fields})


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # The default body repeats the user's input back; return a fixed message instead.
    return error_response(request, 422, "invalid_request")


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    return error_response(request, 500, "internal_error")


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
        return error_response(request, 422, "question_empty")
    if len(question) > get_settings().max_question_chars:
        return error_response(request, 422, "question_too_long")

    try:
        answer = call_model(question)
    except llm.ModelTimeout:
        return error_response(request, 504, "model_timeout")
    except llm.ModelError:
        return error_response(request, 502, "model_unavailable")
    return AskResponse(answer=answer)
