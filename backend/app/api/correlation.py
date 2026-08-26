import logging
import time
import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.logging import set_correlation_id

_logger = logging.getLogger("app.request")


class CorrelationIdMiddleware:
    """ASGI puro (no `BaseHTTPMiddleware`): evita el problema conocido de
    Starlette donde un `ContextVar` fijado en `dispatch()` antes de
    `call_next()` no siempre se propaga de forma confiable al handler
    real (task groups internos de anyio) -- este middleware envuelve la
    app directamente, sin ese salto de task. Reusa `X-Correlation-Id` si
    el caller ya trae uno (tracing distribuido real entre servicios), si
    no genera uno nuevo; lo devuelve también en la respuesta. Log
    estructurado de una línea por request (método/path/status/duración)
    -- `app/core/logging.py` es quien realmente lo serializa a JSON."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-correlation-id")
        correlation_id = incoming.decode() if incoming else str(uuid.uuid4())
        set_correlation_id(correlation_id)

        start = time.monotonic()
        status_holder = {"status": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                response_headers = message.setdefault("headers", [])
                response_headers.append((b"x-correlation-id", correlation_id.encode()))
            await send(message)

        await self.app(scope, receive, send_wrapper)

        _logger.info(
            "request completed",
            extra={
                "method": scope.get("method"),
                "path": scope.get("path"),
                "status": status_holder["status"],
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
