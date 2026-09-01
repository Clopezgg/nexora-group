"""Dirección de tesorería de un AccountingDocument y elegibilidad para
Payment Voucher (ORDEN MAESTRA — FIORI / CASH FLOW / TREASURY DIRECTION).

Regla de negocio (CLAUDE.md §7 — Treasury es dueño del dinero):

- Una **remesa** o un **cobro de cliente** es un INFLOW de tesorería.
- Un **Payment Voucher** documenta un **OUTFLOW** de tesorería (pago que
  sale del banco). Nunca un inflow, nunca una transferencia interna.

La clasificación se deriva de las líneas del asiento contra las cuentas GL
que están 1:1 con un `TreasuryAccount` de la compañía:

    treasury_debits  = Σ debit_amount  de esas líneas   (aumenta el efectivo)
    treasury_credits = Σ credit_amount de esas líneas   (disminuye el efectivo)
    treasury_net     = treasury_debits - treasury_credits

    net > 0                         -> INFLOW
    net < 0                         -> OUTFLOW
    net == 0 y >= 2 cuentas tesor.  -> INTERNAL_TRANSFER  (banco A -> banco B)
    sin líneas de tesorería         -> NON_TREASURY

Solo `OUTFLOW` es elegible para Payment Voucher. El backend es la autoridad
(fail-closed): el endpoint de descarga rechaza cualquier otra dirección con
422 `NXR-VOUCHER-NOT-OUTFLOW`, y el endpoint de candidatos solo devuelve
documentos OUTFLOW — los inflows nunca llegan al browser para ocultarse.

No se modifica ningún asiento (§19): esto es solo lectura y clasificación.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument, JournalLine
from app.models.treasury import TreasuryAccount

INFLOW = "INFLOW"
OUTFLOW = "OUTFLOW"
INTERNAL_TRANSFER = "INTERNAL_TRANSFER"
NON_TREASURY = "NON_TREASURY"

_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class TreasuryDirection:
    direction: str
    treasury_debits: Decimal
    treasury_credits: Decimal
    treasury_net: Decimal
    treasury_account_count: int
    voucher_eligible: bool


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _cash_account_ids(db: Session, company_id: uuid.UUID) -> set[uuid.UUID]:
    return set(
        db.execute(
            select(TreasuryAccount.gl_account_id).where(
                TreasuryAccount.company_id == company_id
            )
        ).scalars()
    )


def classify(db: Session, document: AccountingDocument) -> TreasuryDirection:
    """Clasifica un `AccountingDocument` ya cargado."""
    cash_ids = _cash_account_ids(db, document.company_id)
    lines = db.execute(
        select(JournalLine).where(JournalLine.accounting_document_id == document.id)
    ).scalars().all()

    debits = _ZERO
    credits = _ZERO
    touched: set[uuid.UUID] = set()
    for line in lines:
        if line.account_id not in cash_ids:
            continue
        touched.add(line.account_id)
        debits += Decimal(str(line.debit_amount))
        credits += Decimal(str(line.credit_amount))

    net = _q(debits - credits)
    if not touched:
        direction = NON_TREASURY
    elif net > _ZERO:
        direction = INFLOW
    elif net < _ZERO:
        direction = OUTFLOW
    elif len(touched) >= 2:
        direction = INTERNAL_TRANSFER
    else:
        direction = NON_TREASURY

    return TreasuryDirection(
        direction=direction,
        treasury_debits=_q(debits),
        treasury_credits=_q(credits),
        treasury_net=net,
        treasury_account_count=len(touched),
        voucher_eligible=direction == OUTFLOW,
    )


def classify_document_id(
    db: Session, *, accounting_document_id: uuid.UUID
) -> TreasuryDirection | None:
    document = db.get(AccountingDocument, accounting_document_id)
    if document is None:
        return None
    return classify(db, document)


def outflow_document_ids(db: Session, *, company_id: uuid.UUID) -> set[uuid.UUID]:
    """IDs de los AccountingDocuments de la compañía cuya dirección de
    tesorería es OUTFLOW (candidatos válidos para Payment Voucher)."""
    cash_ids = _cash_account_ids(db, company_id)
    if not cash_ids:
        return set()

    rows = db.execute(
        select(
            JournalLine.accounting_document_id,
            JournalLine.account_id,
            JournalLine.debit_amount,
            JournalLine.credit_amount,
        )
        .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
        .where(
            AccountingDocument.company_id == company_id,
            JournalLine.account_id.in_(cash_ids),
        )
    ).all()

    agg: dict[uuid.UUID, list] = {}
    for doc_id, account_id, debit, credit in rows:
        entry = agg.setdefault(doc_id, [_ZERO, _ZERO, set()])
        entry[0] += Decimal(str(debit))
        entry[1] += Decimal(str(credit))
        entry[2].add(account_id)

    return {
        doc_id
        for doc_id, (debits, credits, _touched) in agg.items()
        if _q(debits - credits) < _ZERO
    }
