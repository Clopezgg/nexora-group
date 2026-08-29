from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import RateLimitExceededError
from app.models.rate_limit import RateLimitBucket


def _locked(bucket: RateLimitBucket, *, limit: int, window_seconds: int) -> bool:
    now = datetime.now(timezone.utc)
    return bucket.count >= limit and now - bucket.window_start < timedelta(seconds=window_seconds)


def assert_not_limited(db: Session, *, bucket_key: str, limit: int, window_seconds: int) -> None:
    bucket = db.execute(
        select(RateLimitBucket).where(RateLimitBucket.bucket_key == bucket_key).with_for_update()
    ).scalar_one_or_none()
    if bucket is None:
        return
    now = datetime.now(timezone.utc)
    if now - bucket.window_start >= timedelta(seconds=window_seconds):
        bucket.window_start = now
        bucket.count = 0
        db.flush()
        return
    if _locked(bucket, limit=limit, window_seconds=window_seconds):
        raise RateLimitExceededError(
            f"Demasiados intentos para '{bucket_key}'; espera antes de volver a intentar."
        )


def reset_bucket(db: Session, *, bucket_key: str) -> None:
    bucket = db.execute(
        select(RateLimitBucket).where(RateLimitBucket.bucket_key == bucket_key).with_for_update()
    ).scalar_one_or_none()
    if bucket is not None:
        bucket.count = 0
        bucket.window_start = datetime.now(timezone.utc)
        db.flush()


def check_and_increment(
    db: Session, *, bucket_key: str, limit: int, window_seconds: int
) -> None:
    """NXR-REQ-0107: defensa de rate-limiting respaldada en PostgreSQL."""
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

    if bucket.count >= limit:
        raise RateLimitExceededError(
            f"Demasiados intentos para '{bucket_key}'; espera antes de volver a intentar."
        )
