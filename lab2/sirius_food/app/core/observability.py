"""Optional Sentry and OpenTelemetry configuration plus trace propagation helpers."""
from contextlib import contextmanager
from typing import MutableMapping

from app.core.config import settings


_tracer = None


def setup_sentry() -> None:
    if not settings.SENTRY_DSN:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )


def setup_tracing(app=None, service_name: str = "sirius-api") -> None:
    global _tracer
    if not settings.OTEL_ENABLED:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT))
    )
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)


def inject_trace_context(headers: MutableMapping[str, str]) -> None:
    if not settings.OTEL_ENABLED:
        return
    from opentelemetry.propagate import inject

    inject(headers)


def current_trace_context() -> dict[str, str]:
    """Return the active W3C trace carrier so it can cross an Outbox boundary."""
    carrier: dict[str, str] = {}
    inject_trace_context(carrier)
    return carrier


def set_current_span_attribute(name: str, value: str) -> None:
    if not settings.OTEL_ENABLED:
        return
    from opentelemetry import trace

    trace.get_current_span().set_attribute(name, value)


def extract_trace_context(headers: MutableMapping | None):
    if not settings.OTEL_ENABLED:
        return None
    from opentelemetry.propagate import extract

    normalized = {str(key): str(value) for key, value in (headers or {}).items()}
    return extract(normalized)


@contextmanager
def traced(name: str, *, context=None, attributes: dict | None = None):
    if not settings.OTEL_ENABLED or _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name, context=context, attributes=attributes or {}) as span:
        yield span
