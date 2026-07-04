"""OpenTelemetry instrumentation for Vera.

Initialises the OTel SDK and instruments FastAPI, httpx, and logging when the
OTLP endpoint is configured. No-op otherwise for local development.
"""

import logging
import os
from urllib.parse import urljoin

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def _parse_headers(raw: str | None) -> dict[str, str] | None:
    """Parse OTEL_EXPORTER_OTLP_HEADERS into a dict.

    Format: ``key1=value1,key2=value2``.  Values may contain ``=`` (e.g. Base64).
    Returns ``None`` when the env var is unset or empty.
    """
    if not raw:
        return None
    headers: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            key, _, value = pair.partition("=")
            headers[key.strip()] = value.strip()
    return headers or None


def setup_telemetry() -> bool:
    """Configure OpenTelemetry if OTLP endpoint is set.

    Returns True if telemetry was initialised, False if skipped.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    trace_endpoint = urljoin(endpoint.rstrip("/") + "/", "v1/traces")
    headers = _parse_headers(os.environ.get("OTEL_EXPORTER_OTLP_HEADERS"))

    resource = Resource.create({
        SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "vera"),
    })

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=trace_endpoint,
                headers=headers,
            )
        )
    )
    trace.set_tracer_provider(provider)

    LoggingInstrumentor().instrument()
    SystemMetricsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    logger.info("OpenTelemetry initialised, exporting to %s", endpoint)
    print(f"[telemetry] OpenTelemetry activo — exportando a {endpoint}", flush=True)
    return True


def instrument_fastapi(app: FastAPI) -> None:
    """Apply FastAPI instrumentation for request tracing."""
    FastAPIInstrumentor.instrument_app(app)
