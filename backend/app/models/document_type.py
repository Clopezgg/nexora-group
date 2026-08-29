from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DOCUMENT_TYPE_SEEDS = (
    ("JRN", "Asiento contable manual", "JRN"),
    ("COR", "Corrección contable", "COR"),
    ("ANU", "Anulación / reversal", "ANU"),
    ("REM", "Remesa", "REM"),
    ("GGE", "Gasto general", "GGE"),
    ("TRF", "Transferencia de tesorería", "TRF"),
    ("CCL", "Ajuste de cierre de caja", "CCL"),
    ("SIN", "Factura de proveedor (accrual)", "SIN"),
    ("PAY", "Pago a proveedor", "PAY"),
    ("CIN", "Factura de cliente", "CIN"),
    ("REC", "Cobro de cliente", "REC"),
    ("PR", "Solicitud de compra", "PR"),
    ("RFQ", "Solicitud de cotización", "RFQ"),
    ("PO", "Orden de compra", "PO"),
    ("GR", "Recepción de mercadería", "GR"),
    ("SEN", "Entrada de servicio", "SEN"),
    ("DEP", "Depreciación de activo fijo", "DEP"),
    ("FUE", "Costo de combustible", "FUE"),
    ("MNT", "Costo de mantenimiento", "MNT"),
    ("LAB", "Costo de mano de obra aprobada", "LAB"),
    ("RFI", "Request For Information", "RFI"),
    ("SUB", "Submittal", "SUB"),
)


class DocumentType(Base):
    __tablename__ = "document_types"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    number_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
