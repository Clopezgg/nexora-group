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
    # Track A - Financial Core (orden maestra §25).
    ("REM", "Remesa", "REM"),
    ("GGE", "Gasto general", "GGE"),
    ("TRF", "Transferencia de tesorería", "TRF"),
    ("CCL", "Ajuste de cierre de caja", "CCL"),
    ("SIN", "Factura de proveedor (accrual)", "SIN"),
    ("PAY", "Pago a proveedor", "PAY"),
    ("CIN", "Factura de cliente", "CIN"),
    ("REC", "Cobro de cliente", "REC"),
    # Track C -- Procurement (orden maestra §25/§44-51).
    ("PR", "Solicitud de compra", "PR"),
    ("RFQ", "Solicitud de cotización", "RFQ"),
    ("PO", "Orden de compra", "PO"),
    ("GR", "Recepción de mercadería", "GR"),
    # "SIN" ya está tomado por Track A (Factura de proveedor); Track C usa
    # "SEN" para la entrada de servicio (orden maestra §44-51) para evitar
    # colisión de PK en `document_types.code`.
    ("SEN", "Entrada de servicio", "SEN"),
    # Track D -- Enterprise Resources (orden maestra §62-69).
    ("DEP", "Depreciación de activo fijo", "DEP"),
)


class DocumentType(Base):
    __tablename__ = "document_types"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    number_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
