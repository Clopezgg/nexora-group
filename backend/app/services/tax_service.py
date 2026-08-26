import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.domain.errors import TaxCodeExistsError
from app.models.tax import TaxCode
from app.repositories import tax_repository

"""Tax architecture (NXR-REQ-0006, orden maestra). `TaxCode`/`TaxLine` ya
existían como modelo de datos y `posting_service.post_manual` ya acepta
`tax_lines` -- lo que faltaba era la gestión real de `TaxCode`
(crear/listar por company) y una función de cálculo real y probada.
`compute_tax` es pura (no toca DB, sin efectos secundarios): cualquier
dominio (AP, AR, Procurement) la puede usar cuando decida adoptar
impuesto calculado en vez del `tax_amount` manual que aceptan hoy -- ver
docs/DEFERRED.md para el estado de esa adopción por dominio. No existe
todavía ninguna FX policy en este codebase (ver
`ProcurementCurrencyMismatchError`/`BudgetCurrencyMismatchError`); tax es
independiente de moneda -- el porcentaje se aplica sobre `base_amount` en
la moneda que sea, no hay conversión involucrada."""


def create_tax_code(
    db: Session, *, company_id: uuid.UUID, code: str, name: str, rate_percent: Decimal,
    commit: bool = True,
) -> TaxCode:
    if tax_repository.get_tax_code_by_code(db, company_id=company_id, code=code) is not None:
        raise TaxCodeExistsError(f"Ya existe un TaxCode con código {code!r} en esta compañía")
    tax_code = tax_repository.create_tax_code(
        db, company_id=company_id, code=code, name=name, rate_percent=rate_percent
    )
    if commit:
        db.commit()
        db.refresh(tax_code)
    else:
        db.flush()
    return tax_code


def list_tax_codes(db: Session, *, company_id: uuid.UUID) -> list[TaxCode]:
    return tax_repository.list_tax_codes(db, company_id=company_id)


def compute_tax(base_amount: Decimal, tax_code: TaxCode) -> Decimal:
    """`base_amount * rate_percent / 100`, redondeado a 2 decimales
    (moneda) con HALF_UP -- mismo criterio que `workforce_service.
    approve_time_entry` usa para `labor_cost`. El caller decide si arma
    un `TaxLine`/`JournalLineInput` con el resultado; esta función nunca
    persiste nada."""
    return (base_amount * tax_code.rate_percent / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
