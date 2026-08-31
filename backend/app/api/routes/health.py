from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.integrations.azure_blob import evidence_storage_is_reachable

router = APIRouter(tags=["health"])


@router.get("/healthz")
@router.get("/api/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
@router.get("/api/readyz", include_in_schema=False)
def readyz(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as error:  # pragma: no cover - depende de infraestructura real
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Base de datos no disponible: {error}",
        ) from error

    settings = get_settings()
    if settings.evidence_backend == "azure_blob":
        ok, detail = evidence_storage_is_reachable(settings)
        if not ok:
            # No se reporta healthy si el almacenamiento de evidencias esta
            # configurado pero la Managed Identity no puede alcanzarlo. El
            # detalle es solo el tipo de excepcion, nunca URL/credencial.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Almacenamiento de evidencias no disponible ({detail or 'desconocido'})",
            )

    return {"status": "ok"}
