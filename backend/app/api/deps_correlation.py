from app.core.logging import get_correlation_id as _get_correlation_id

"""NXR-REQ-0108: única fuente de verdad -- `CorrelationIdMiddleware`
(app/api/correlation.py) ya fijó este valor para toda la request antes
de que cualquier dependencia se resuelva, así que este `Depends()`
simplemente lo lee del mismo `ContextVar` que usan los logs, el audit
log y `error_handlers.py`. Ya no parsea el header por su cuenta -- eso
generaba un id distinto por cada `Depends(get_correlation_id)` en rutas
distintas cuando el caller no mandaba `X-Correlation-Id`."""


def get_correlation_id() -> str:
    return _get_correlation_id()
