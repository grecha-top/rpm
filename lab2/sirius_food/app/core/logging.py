"""Structured JSON logging shared by the API and workers."""
import logging
import sys

import structlog

from app.core.correlation import get_correlation_id


def _add_service_and_correlation(_, __, event_dict):
    event_dict.setdefault("service", "sirius-food")
    event_dict.setdefault("correlation_id", get_correlation_id())
    return event_dict


def setup_logging(level: int = logging.INFO) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        _add_service_and_correlation,
        structlog.stdlib.add_log_level,
        timestamper,
    ]
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(*args, **kwargs):
    return structlog.get_logger(*args, **kwargs)
