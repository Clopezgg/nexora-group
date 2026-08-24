from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Catálogo de tipos de documento y su prefijo de numeración (ver docs/ACCOUNTING.md
# sección "Number sequences"). Cada track de dominio agrega los suyos aquí cuando
# construye su módulo (REM, GGE, PR, RFQ, PO, ...); este track solo registra el
# necesario para el Posting Engine (JRN, COR, ANU).
DOCUMENT_TYPE_SEEDS = (
    ("JRN", "Asiento contable manual", "JRN"),
    ("COR", "Corrección contable", "COR"),
    ("ANU", "Anulación / reversal", "ANU"),
    # Track C -- Procurement (orden maestra §25/§44-51).
    ("PR", "Solicitud de compra", "PR"),
    ("RFQ", "Solicitud de cotización", "RFQ"),
    ("PO", "Orden de compra", "PO"),
    ("GR", "Recepción de mercadería", "GR"),
    ("SIN", "Entrada de servicio", "SIN"),
)


class DocumentType(Base):
    __tablename__ = "document_types"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    number_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
