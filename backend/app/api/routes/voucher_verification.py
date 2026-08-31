"""Verificación pública de comprobantes (orden maestra correctiva §41).

Endpoint SIN autenticación y de exposición mínima. Rate-limited por IP
(respaldo PostgreSQL, mismo mecanismo que el login). Nunca devuelve cuenta
bancaria completa, evidencia, IDs técnicos, blob keys, metadata de auditoría
ni secretos.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import rate_limit_service, voucher_verification_service

router = APIRouter(tags=["verificacion"])


@router.get("/verificar/comprobante/{token}")
def verificar_comprobante(token: str, request: Request, db: Session = Depends(get_db)) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_service.check_and_increment(
        db,
        bucket_key=f"voucher-verify:{client_ip}",
        limit=60,
        window_seconds=300,
    )

    if not token or len(token) > 64:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comprobante no encontrado")

    result = voucher_verification_service.verify(db, token=token)
    db.commit()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontramos un comprobante con ese código de verificación.",
        )
    return result
