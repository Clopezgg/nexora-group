from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

"""NXR-REQ-0107 (Security headers, §121). El backend es una API JSON
pura -- ningún endpoint de negocio devuelve HTML para renderizar, así
que puede ser estricto: `X-Content-Type-Options`/`X-Frame-Options`/
`Referrer-Policy` son universales y nunca rompen nada (son correctos
también sobre las respuestas HTML del propio FastAPI, `/docs`/`/redoc`).
`Content-Security-Policy` se omite deliberadamente en `/docs`/`/redoc`
(Swagger/ReDoc cargan su JS/CSS real desde un CDN -- una CSP estricta
ahí las rompe) y se aplica estricta (`default-src 'none'`) en todo lo
demás, reforzando que ninguna respuesta JSON debería ejecutarse como
página. `Strict-Transport-Security` solo tiene efecto real sobre HTTPS
-- se omite en dev para no confundir un smoke test local corriendo por
HTTP, se aplica en producción."""

_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def register_security_headers(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
