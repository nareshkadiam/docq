import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app, get_model_caller

client = TestClient(app)

SECRET_QUESTION = "what-is-my-secret-question-xyz"


@pytest.fixture(autouse=True)
def never_call_real_model(monkeypatch):
    """Safety net: if any test reaches the real Gen AI client, fail loudly."""

    def boom(*args, **kwargs):
        raise AssertionError("A test tried to create a real Gemini client")

    monkeypatch.setattr(llm.genai, "Client", boom)
    llm._client.cache_clear()
    yield
    app.dependency_overrides.clear()


def use_fake_model(fake):
    app.dependency_overrides[get_model_caller] = lambda: fake


def test_ask_returns_answer():
    use_fake_model(lambda question: f"echo: {question}")
    response = client.post("/ask", json={"question": "What is Cloud Run?"})
    assert response.status_code == 200
    assert response.json() == {"answer": "echo: What is Cloud Run?"}


def test_ask_rejects_empty_question():
    use_fake_model(lambda question: "should not be called")
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 422
    assert response.json() == {"error": "question_empty"}


def test_ask_rejects_too_long_question(monkeypatch):
    monkeypatch.setenv("MAX_QUESTION_CHARS", "10")
    use_fake_model(lambda question: "should not be called")
    response = client.post("/ask", json={"question": "x" * 11})
    assert response.status_code == 422
    assert response.json() == {"error": "question_too_long"}


def test_ask_rejects_missing_question_without_echoing_input():
    response = client.post("/ask", json={"wrong_field": SECRET_QUESTION})
    assert response.status_code == 422
    assert SECRET_QUESTION not in response.text


def test_model_failure_returns_clear_error():
    def fail(question):
        raise llm.ModelError("internal detail that must not leak")

    use_fake_model(fail)
    response = client.post("/ask", json={"question": "hello"})
    assert response.status_code == 502
    assert response.json() == {"error": "model_unavailable"}
    assert "internal detail" not in response.text


def test_model_timeout_returns_504():
    def slow(question):
        raise llm.ModelTimeout()

    use_fake_model(slow)
    response = client.post("/ask", json={"question": "hello"})
    assert response.status_code == 504
    assert response.json() == {"error": "model_timeout"}


def test_unexpected_error_returns_generic_500():
    def crash(question):
        raise RuntimeError("stack trace detail")

    use_fake_model(crash)
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.post("/ask", json={"question": "hello"})
    assert response.status_code == 500
    assert response.json() == {"error": "internal_error"}


def test_real_client_is_never_built_by_tests():
    # The autouse fixture makes Client() raise; asking through llm directly must
    # surface it as ModelError, proving the fixture is active and errors are wrapped.
    from app.config import get_settings

    with pytest.raises(llm.ModelError):
        llm.ask_model("hi", get_settings())
