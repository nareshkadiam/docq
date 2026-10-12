import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project: str | None
    location: str
    model: str
    max_question_chars: int
    max_output_tokens: int
    timeout_seconds: float


def get_settings() -> Settings:
    """Read settings from environment variables, with safe defaults.

    Read on every call (not cached) so tests and redeploys can change them.
    """
    return Settings(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GEMINI_LOCATION", "eu"),
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        max_question_chars=int(os.getenv("MAX_QUESTION_CHARS", "1000")),
        max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "256")),
        timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "20")),
    )
