"""The only module that talks to Gemini on Vertex AI.

Authentication uses Application Default Credentials: no API key, no key file.
Locally ADC is your own login (gcloud auth application-default login); on Cloud
Run it is the service account the service runs as.
"""

from functools import lru_cache

import httpx
from google import genai
from google.genai import errors, types

from app.config import Settings

SYSTEM_INSTRUCTION = "Answer the question briefly and accurately. If you are unsure, say so."


class ModelError(Exception):
    """The model call failed (permissions, quota, outage, blocked or empty answer)."""


class ModelTimeout(Exception):
    """The model call took longer than the configured timeout."""


@lru_cache
def _client(project: str | None, location: str, timeout_seconds: float) -> genai.Client:
    return genai.Client(
        enterprise=True,
        project=project,
        location=location,
        http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
    )


def ask_model(question: str, settings: Settings) -> str:
    """Send one question to the model and return the answer text."""
    try:
        client = _client(settings.project, settings.location, settings.timeout_seconds)
        response = client.models.generate_content(
            model=settings.model,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=settings.max_output_tokens,
            ),
        )
    except httpx.TimeoutException as exc:
        raise ModelTimeout from exc
    except errors.APIError as exc:
        raise ModelError from exc
    except Exception as exc:  # network errors, auth problems: never leak details to the caller
        raise ModelError from exc

    if not response.text:
        raise ModelError("empty answer")
    return response.text
