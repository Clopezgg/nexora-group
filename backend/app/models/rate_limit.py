from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RateLimitBucket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """NXR-REQ-0107: contador de ventana fija respaldado en PostgreSQL (no
    memoria de proceso -- backend stateless, orden maestra §3) para
    defensa de rate-limiting a nivel de aplicación, independiente de
    cualquier WAF/Front Door de Azure. Una fila por `bucket_key` (p.ej.
    "login:<ip>"), reutilizada y reseteada in-place cuando expira su
    ventana -- nunca crece sin límite por request."""

    __tablename__ = "rate_limit_buckets"

    bucket_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
