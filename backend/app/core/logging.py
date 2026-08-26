import contextvars
import json
import logging
import sys

"""NXR-REQ-0108 (Observability). Un `correlation_id` real por request --
antes solo existía como un `Depends()` que cada ruta llamaba por su
cuenta (parseando el header `X-Correlation-Id` de nuevo cada vez), sin
relación con lo que terminaba en los logs de Python ni en el body de un
error (`error_handlers.py` generaba su propio `uuid.uuid4()` random,
desconectado). Ahora hay una sola fuente de verdad: el ASGI middleware
(`app/api/correlation.py`) fija este ContextVar una vez por request,
antes de que se resuelva cualquier dependencia o handler -- todo lo que
lea `get_correlation_id()` durante esa request (logging, audit,
error handlers, CSRF guard) ve el mismo valor."""

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)

_EXTRA_FIELDS = ("method", "path", "status", "duration_ms")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlationId": getattr(record, "correlation_id", "-"),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotente: reemplaza los handlers del root logger una sola vez
    con el formatter JSON, sin duplicar salida en llamadas repetidas
    (create_app() en tests/reloads)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_CorrelationIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
