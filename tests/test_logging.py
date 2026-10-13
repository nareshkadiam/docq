import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app import llm, logs
from app.main import app, get_model_caller

client = TestClient(app)

SECRET_QUESTION = "what-is-my-secret-question-xyz"
SECRET_ANSWER = "SECRET-ANSWER-abc"
SECRET_ERROR_TEXT = "SECRET-ERROR-TEXT-qrs"
TRACE_ID = "105445aa7843bc8bf206b12000100000"


@pytest.fixture(autouse=True)
def never_call_real_model(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("A test tried to create a real Gemini client")

    monkeypatch.setattr(llm.genai, "Client", boom)
    llm._client.cache_clear()
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def captured():
    """Capture what the docq logger prints, formatted exactly as in production."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logs.JsonFormatter())
    logger = logging.getLogger("docq")
    logger.addHandler(handler)
    yield stream
    logger.removeHandler(handler)


def use_fake_model(fake):
    app.dependency_overrides[get_model_caller] = lambda: fake


def one_entry(stream: io.StringIO) -> dict:
    """Exactly one non-empty line, and it must be valid JSON."""
    lines = [line for line in stream.getvalue().splitlines() if line]
    assert len(lines) == 1, lines
    return json.loads(lines[0])


def test_success_logs_one_json_line_with_metadata(captured):
    use_fake_model(lambda question: SECRET_ANSWER)
    client.post("/ask", json={"question": SECRET_QUESTION})
    entry = one_entry(captured)
    assert entry["severity"] == "INFO"
    assert entry["message"] == "request"
    assert entry["method"] == "POST"
    assert entry["path"] == "/ask"
    assert entry["status"] == 200
    assert isinstance(entry["latency_ms"], int)
    assert entry["question_len"] == len(SECRET_QUESTION)
    assert "error" not in entry
    assert "exception_type" not in entry


def test_health_logs_info_without_question_len(captured):
    client.get("/health")
    entry = one_entry(captured)
    assert entry["severity"] == "INFO"
    assert entry["status"] == 200
    assert "question_len" not in entry


@pytest.mark.parametrize(
    ("fake", "payload", "status", "severity", "error"),
    [
        (lambda q: "x", {"question": "   "}, 422, "WARNING", "question_empty"),
        (lambda q: "x", {"wrong_field": SECRET_QUESTION}, 422, "WARNING", "invalid_request"),
        (
            lambda q: (_ for _ in ()).throw(llm.ModelTimeout()),
            {"question": "hello"},
            504,
            "ERROR",
            "model_timeout",
        ),
        (
            lambda q: (_ for _ in ()).throw(llm.ModelError(SECRET_ERROR_TEXT)),
            {"question": "hello"},
            502,
            "ERROR",
            "model_unavailable",
        ),
    ],
)
def test_failures_log_severity_and_error_code(captured, fake, payload, status, severity, error):
    use_fake_model(fake)
    client.post("/ask", json=payload)
    entry = one_entry(captured)
    assert entry["status"] == status
    assert entry["severity"] == severity
    assert entry["error"] == error
    assert SECRET_ERROR_TEXT not in captured.getvalue()
    assert SECRET_QUESTION not in captured.getvalue()


def test_too_long_question_logs_error_code(captured, monkeypatch):
    monkeypatch.setenv("MAX_QUESTION_CHARS", "10")
    use_fake_model(lambda q: "x")
    client.post("/ask", json={"question": "x" * 11})
    entry = one_entry(captured)
    assert entry["error"] == "question_too_long"
    assert entry["severity"] == "WARNING"
    assert entry["question_len"] == 11


def test_unexpected_error_logs_class_name_but_not_message(captured):
    def crash(question):
        raise RuntimeError(SECRET_ERROR_TEXT + SECRET_QUESTION)

    use_fake_model(crash)
    safe_client = TestClient(app, raise_server_exceptions=False)
    safe_client.post("/ask", json={"question": SECRET_QUESTION})
    entry = one_entry(captured)
    assert entry["status"] == 500
    assert entry["severity"] == "ERROR"
    assert entry["error"] == "internal_error"
    assert entry["exception_type"] == "RuntimeError"
    assert SECRET_ERROR_TEXT not in captured.getvalue()
    assert SECRET_QUESTION not in captured.getvalue()


def test_question_and_answer_never_reach_the_log_on_success(captured):
    use_fake_model(lambda question: SECRET_ANSWER)
    client.post("/ask", json={"question": SECRET_QUESTION})
    assert SECRET_QUESTION not in captured.getvalue()
    assert SECRET_ANSWER not in captured.getvalue()


def test_trace_field_present_with_valid_header_and_project(captured, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p1")
    client.get("/health", headers={"X-Cloud-Trace-Context": f"{TRACE_ID}/12345;o=1"})
    entry = one_entry(captured)
    assert entry[logs.TRACE_KEY] == f"projects/p1/traces/{TRACE_ID}"


def test_bad_unrelated_setting_does_not_break_logging(captured, monkeypatch):
    monkeypatch.setenv("MAX_QUESTION_CHARS", "not-a-number")
    client.get("/health", headers={"X-Cloud-Trace-Context": f"{TRACE_ID}/1;o=1"})
    assert one_entry(captured)["status"] == 200


def test_trace_field_absent_without_header(captured, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p1")
    client.get("/health")
    assert logs.TRACE_KEY not in one_entry(captured)


def test_trace_field_absent_without_project(captured):
    client.get("/health", headers={"X-Cloud-Trace-Context": f"{TRACE_ID}/1;o=1"})
    assert logs.TRACE_KEY not in one_entry(captured)


@pytest.mark.parametrize(
    "header",
    ["", "garbage", TRACE_ID[:-1], TRACE_ID + "0", f"{TRACE_ID}/abc", f'{TRACE_ID}"}}', "z" * 32],
)
def test_malformed_trace_header_is_ignored(header):
    assert logs.trace_from_header(header, "p1") is None


def test_trace_header_without_span_or_options_is_accepted():
    assert logs.trace_from_header(TRACE_ID, "p1") == f"projects/p1/traces/{TRACE_ID}"


def test_quote_in_path_still_gives_one_valid_json_line(captured):
    client.get("/a%22b")  # decoded path contains a double quote
    entry = one_entry(captured)
    assert entry["path"] == '/a"b'
    assert entry["status"] == 404
    assert entry["severity"] == "WARNING"


def test_formatter_escapes_newlines_and_quotes_into_one_line():
    record = logging.LogRecord("docq", logging.INFO, "f.py", 1, "request", None, None)
    record.fields = {"path": '/a"b\nc\r\nd'}
    line = logs.JsonFormatter().format(record)
    assert "\n" not in line and "\r" not in line
    assert json.loads(line)["path"] == '/a"b\nc\r\nd'
