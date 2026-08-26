from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Company es master data real (orden maestra §16), no solo un nombre: soporta
# multi-company desde el modelo (Digital Core GROUP -> COMPANY -> PROJECT ->
# WBS, ver CLAUDE.md §6). code/legal_name/fiscal_id son opcionales por ahora
# porque las companies creadas antes de este track (si las hay) solo tenían
# `name` -- se completan al editar, no se fuerza backfill aquí.


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    functional_currency_code: Mapped[str | None] = mapped_column(
        String(3), ForeignKey("currencies.code"), nullable=True
    )
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    fiscal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="company")
