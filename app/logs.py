"""One JSON object per line, in the shape Cloud Logging understands.

Cloud Run treats a stdout line that is valid JSON as structured: `severity` sets the
log level and `logging.googleapis.com/trace` ties the entry to a request's trace.
Only a fixed set of metadata fields is ever passed in. Never add the question, the
answer or an exception message here (CLAUDE.md rule 8).
"""

import json
import logging
import re

TRACE_KEY = "logging.googleapis.com/trace"

# Cloud Run sets X-Cloud-Trace-Context: TRACE_ID/SPAN_ID;o=1 (trace id = 32 hex chars).
_TRACE_HEADER = re.compile(r"^([0-9a-fA-F]{32})(?:/\d+)?(?:;o=\d)?$")


class JsonFormatter(logging.Formatter):
    """Format a record as a single-line JSON object: severity, message, then the fields."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {"severity": record.levelname, "message": record.getMessage()}
        entry.update(getattr(record, "fields", {}))
        # json.dumps escapes quotes and newlines, so the output is always one line.
        return json.dumps(entry)


def get_logger() -> logging.Logger:
    logger = logging.getLogger("docq")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def level_for(status: int) -> int:
    """INFO below 400, WARNING for client errors, ERROR for server errors."""
    if status >= 500:
        return logging.ERROR
    if status >= 400:
        return logging.WARNING
    return logging.INFO


def trace_from_header(header: str | None, project: str | None) -> str | None:
    """Return the Cloud Logging trace name, or None if the header or project is missing/malformed.

    The header is only a string from the caller: it is used to label logs, nothing else.
    """
    if not header or not project:
        return None
    match = _TRACE_HEADER.match(header.strip())
    if not match:
        return None
    return f"projects/{project}/traces/{match.group(1).lower()}"
