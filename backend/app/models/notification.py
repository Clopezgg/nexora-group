import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

"""Notifications (Track G / Platform, NXR-REQ-0091/0092). Entidad genérica
in-app (sin email/push, ver docs/superpowers/specs/2026-08-25-track-g-
workflow-audit-design.md) creada en los mismos puntos de evento que
`ApprovalRequest`: al crear una solicitud (notifica a `assigned_to`) y al
decidirla (notifica a `requested_by`). Pertenece a un usuario
(`recipient_user_id`), no a una compañía -- por eso su verificación de
propiedad en la API es directa contra el usuario autenticado, no
`assert_company_access`."""


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
