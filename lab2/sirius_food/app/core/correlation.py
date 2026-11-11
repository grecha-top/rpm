"""Correlation ID propagation for HTTP requests and background consumers."""
from contextvars import ContextVar, Token
from uuid import uuid4

from fastapi import Request

from app.core.observability import set_current_span_attribute


CORRELATION_HEADER = "X-Correlation-ID"
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="unknown")


def get_correlation_id() -> str:
    return _correlation_id.get()


def bind_correlation_id(value: str | None = None) -> Token:
    return _correlation_id.set(value or str(uuid4()))


def reset_correlation_id(token: Token) -> None:
    _correlation_id.reset(token)


async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid4())
    token = bind_correlation_id(correlation_id)
    set_current_span_attribute("correlation_id", correlation_id)
    request.state.correlation_id = correlation_id
    try:
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
    finally:
        reset_correlation_id(token)
