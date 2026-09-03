"""Registro central de los hooks de reversión del Posting Engine.

``posting_service.reverse_document`` sincroniza el estado del documento fuente
(factura, activo, etc.) al revertir su asiento a través de un hook por
``source_type``. Ese registro vivía únicamente en el arranque de la app
(``app.main``), de modo que cualquier proceso que revierta un asiento **sin**
importar ``app.main`` -- p. ej. el runner de mantenimiento
``scripts.financial_reconciliation`` -- dejaba la factura ``APPROVED``
apuntando a un accrual ya ``REVERSED`` (pagable de nuevo aunque el GL ya no
refleje el gasto).

Este módulo expone un único punto de registro idempotente que llaman tanto
``app.main`` como el runner de mantenimiento.
"""

from __future__ import annotations

from app.services import posting_service


def register_default_reversal_hooks() -> None:
    """Registra los hooks de reversión estándar. Idempotente."""
    from app.services import ap_service, ar_service, asset_service

    posting_service.register_reversal_hook(
        "supplier_invoice",
        lambda db, source_id, document_type_code: ap_service.apply_accrual_reversal(
            db, invoice_id=source_id, document_type_code=document_type_code
        ),
    )
    posting_service.register_reversal_hook(
        "customer_invoice",
        lambda db, source_id, document_type_code: ar_service.apply_invoice_reversal(
            db, invoice_id=source_id, document_type_code=document_type_code
        ),
    )
    posting_service.register_reversal_hook(
        "fixed_asset",
        lambda db, source_id, document_type_code: asset_service.apply_capitalization_reversal(
            db, asset_id=source_id, document_type_code=document_type_code
        ),
    )
