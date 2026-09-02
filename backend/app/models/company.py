import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project

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
    # Identidad de comprobantes (orden maestra Phase 2). El pagador se asigna
    # una sola vez y luego es read-only (mismo patrón que `code`); el
    # aprobador es configurable. Se imprimen en el PDF -- nunca hardcodeados.
    voucher_payer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voucher_approver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Theme Engine (orden maestra Phase 8) -- SOLO presentación. Predeterminados
    # de la compañía; cada usuario puede sobreescribirlos en sus preferencias.
    default_theme_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_density: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Perfil documental de la compañía (orden maestra final §29). Se imprimen
    # en el comprobante -- nunca hardcodeados. Configurables desde
    # Configuración -> Perfil de empresa -> Documentos.
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voucher_footer_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Enlace INFORMATIVO a Evidence (mismo criterio que Evidence.entity_id:
    # sin FK, para no crear un ciclo companies<->evidence). Se valida en el
    # servicio que la evidencia pertenezca a la compañía.
    logo_evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    signature_evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Cuenta contable para ANTICIPOS a proveedores/contratistas (§14). Sin ella,
    # el pago de un anticipo falla cerrado — nunca se usa una cuenta arbitraria.
    # Sin FK a nivel DB (mismo criterio que logo/signature: evita el ciclo
    # companies<->accounts<->chart_of_accounts); se valida en el servicio.
    supplier_advance_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    projects: Mapped[list["Project"]] = relationship(back_populates="company")
