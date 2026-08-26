from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency import Currency
from app.models.document_type import DOCUMENT_TYPE_SEEDS, DocumentType

# Catálogos globales mínimos para que el Posting Engine y Master Data
# puedan funcionar desde el primer arranque. HNL (Lempira, moneda funcional
# típica de un proyecto de construcción en Honduras) y USD porque buena
# parte de contratos/importaciones de construcción se cotizan en dólares.
_BASE_CURRENCIES = (
    ("HNL", "Lempira hondureño", "L"),
    ("USD", "Dólar estadounidense", "$"),
)


def ensure_base_currencies(db: Session) -> None:
    existing = {code for code in db.execute(select(Currency.code)).scalars()}
    for code, name, symbol in _BASE_CURRENCIES:
        if code not in existing:
            db.add(Currency(code=code, name=name, symbol=symbol))
    db.flush()


def ensure_base_document_types(db: Session) -> None:
    existing = {code for code in db.execute(select(DocumentType.code)).scalars()}
    for code, name, prefix in DOCUMENT_TYPE_SEEDS:
        if code not in existing:
            db.add(DocumentType(code=code, name=name, number_prefix=prefix))
    db.flush()
