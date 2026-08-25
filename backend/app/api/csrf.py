import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

"""NXR-REQ-0008 (CSRF). Decisión explícita: la sesión vive en una cookie
httponly (`SameSite=Lax` en dev, `SameSite=None; Secure` en producción --
frontend y backend en subdominios distintos, ver auth.py). `SameSite=Lax`
ya bloquea la mayoría de CSRF en dev, pero en producción `SameSite=None`
es cross-site por diseño, así que SameSite por sí solo no alcanza ahí.
CORS con `allow_origins=[frontend_url]` ya bloquea cualquier fetch/XHR con
`Content-Type: application/json` desde otro origen (dispara preflight,
que solo el origen configurado puede pasar) -- eso cubre casi toda la
API, que es JSON puro. La excepción real es `POST /api/evidence`
(`multipart/form-data`, ver evidence.py): ese Content-Type NO dispara
preflight, así que un <form> HTML malicioso en otro sitio SÍ podría
enviarlo con las cookies de la víctima. En vez de una excepción puntual
para ese endpoint, se valida el header `Origin` en TODA mutación
(POST/PUT/PATCH/DELETE) -- defensa uniforme, no depende de que cada
nuevo endpoint recuerde aplicarla. Cuando `Origin` está ausente (curl,
TestClient, health checks) se permite -- eso no es el vector de CSRF
(que exige que el navegador de la víctima haga la petición, y los
navegadores siempre mandan `Origin` en peticiones cross-site no
triviales); rechazar ahí solo rompería clientes legítimos no-navegador
sin mitigar ningún ataque real."""

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CsrfOriginGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in _UNSAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is not None and origin != get_settings().frontend_url:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "NXR-AUTH-001",
                            "message": "Origin no autorizado para esta operación",
                            "field": None,
                            "correlationId": str(uuid.uuid4()),
                        }
                    },
                )
        return await call_next(request)


def register_csrf_guard(app: FastAPI) -> None:
    app.add_middleware(CsrfOriginGuardMiddleware)
