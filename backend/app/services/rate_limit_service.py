from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import RateLimitExceededError
from app.models.rate_limit import RateLimitBucket


def check_and_increment(
    db: Session, *, bucket_key: str, limit: int, window_seconds: int
) -> None:
    """NXR-REQ-0107: defensa de rate-limiting de aplicación, real y
    respaldada en PostgreSQL (no memoria de proceso -- backend stateless,
    orden maestra §3, corre igual con 1 o N réplicas de Container Apps).
    Ventana fija reutilizada in-place: una sola fila por `bucket_key`, se
    resetea sola cuando expira en vez de acumular filas sin límite.

    Mismo patrón SAVEPOINT que `numbering_service`/`idempotency_service`
    para el create-race de la primera vez que se ve un `bucket_key`: dos
    requests concurrentes del mismo IP pueden ver `bucket is None` a la
    vez antes de que cualquiera haga commit del INSERT -- `bucket_key` es
    `unique=True` (constraint real), así que sin manejar esa colisión
    explícitamente el request que pierde la carrera recibiría un
    `IntegrityError` sin capturar en vez de simplemente contarse.

    Levanta `RateLimitExceededError` (mapeado a 429) si el conteo, tras
    incrementar, supera `limit` dentro de la ventana vigente. El caller
    es responsable de hacer commit de la transacción."""
    now = datetime.now(timezone.utc)
    bucket = db.execute(
        select(RateLimitBucket).where(RateLimitBucket.bucket_key == bucket_key).with_for_update()
    ).scalar_one_or_none()

    if bucket is None:
        savepoint = db.begin_nested()
        try:
            bucket = RateLimitBucket(bucket_key=bucket_key, window_start=now, count=0)
            db.add(bucket)
            db.flush()
            savepoint.commit()
        except IntegrityError:
            savepoint.rollback()
            bucket = db.execute(
                select(RateLimitBucket)
                .where(RateLimitBucket.bucket_key == bucket_key)
                .with_for_update()
            ).scalar_one()

    if now - bucket.window_start >= timedelta(seconds=window_seconds):
        bucket.window_start = now
        bucket.count = 0

    bucket.count += 1
    db.flush()

    if bucket.count > limit:
        raise RateLimitExceededError(
            f"Demasiados intentos para '{bucket_key}'; espera antes de volver a intentar."
        )
