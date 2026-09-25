"""Structured logging. Transcript text and phone numbers are never logged at INFO or above."""

from __future__ import annotations

import logging

import structlog

REDACTED_KEYS = {
    "transcript",
    "window_text",
    "partial_text",
    "text",
    "from_number",
    "phone",
    "From",
}


def _redact(_logger, _method, event_dict):
    level = event_dict.get("level", "info")
    if level in {"debug"}:
        return event_dict
    for key in list(event_dict):
        if key in REDACTED_KEYS:
            event_dict[key] = "[redacted]"
    return event_dict


def configure_logging(level: str = "INFO", json_output: bool = False) -> None:
    logging.basicConfig(level=level.upper(), format="%(message)s")
    renderer = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )
