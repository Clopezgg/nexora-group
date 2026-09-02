"""Reconciliación financiera productiva — inspect / preview / apply (§5/§6/§55).

Herramienta de mantenimiento invocada por
``.github/workflows/maintenance-financial-reconciliation.yml`` contra la base
de datos productiva a través de la misma infraestructura OIDC que usa el
deploy. Nunca imprime cadenas de conexión ni secretos.

Modos:

* ``inspect``  — sólo lectura; delega en ``financial_event_inspect``.
* ``preview``  — calcula ANTES/DESPUÉS de reconstruir el plan de un contrato
  con el motor canónico; NO persiste.
* ``apply``    — persiste la reconstrucción y registra un ``AuditLog``. Exige
  ``--confirm APPLY`` y un ``--reason`` de ≥ 15 caracteres. Fail-closed si el
  plan ya tiene pagos aplicados.

Ejemplos::

    python -m scripts.financial_reconciliation --mode inspect \
        --contract-number 10101960 --project-code 3201 --amount 50000

    python -m scripts.financial_reconciliation --mode preview \
        --contract-number 10101960 --advance-amount 50000 \
        --advance-due-date 2026-08-22 --retention 0 \
        --regular-months 7 --due-day 1 --first-period 2026-09

    python -m scripts.financial_reconciliation --mode apply \
        --contract-number 10101960 --advance-amount 50000 \
        --advance-due-date 2026-08-22 --retention 0 \
        --regular-months 7 --due-day 1 --first-period 2026-09 \
        --confirm APPLY --reason "Plan legacy sin anticipo; corrección autorizada ORDEN MAESTRA §10"
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.contract_payment import ContractPaymentSchedule
from app.models.supplier import SupplierContract
from app.services import audit_service
from app.services import contract_payment_service as cps
from app.services.reversal_hooks import register_default_reversal_hooks
from scripts.financial_event_inspect import (
    Filters,
    _json_default,
    _print_human,
    inspect,
)

_APPLY_TOKEN = "APPLY"
_MIN_REASON = 15


def _first_period(value: str) -> date:
    """Acepta 'YYYY-MM' o 'YYYY-MM-DD'."""
    parts = value.split("-")
    if len(parts) == 2:
        return date(int(parts[0]), int(parts[1]), 1)
    return date.fromisoformat(value)


def _resolve_contract_schedule(
    db: Session, *, contract_number: str
) -> tuple[SupplierContract, ContractPaymentSchedule]:
    contract = db.execute(
        select(SupplierContract).where(SupplierContract.contract_number == contract_number)
    ).scalars().first()
    if contract is None:
        raise SystemExit(f"No existe un contrato con número {contract_number!r}.")
    schedule = db.execute(
        select(ContractPaymentSchedule).where(
            ContractPaymentSchedule.supplier_contract_id == contract.id
        )
    ).scalars().first()
    if schedule is None:
        raise SystemExit(f"El contrato {contract_number} no tiene plan de pagos que reconstruir.")
    return contract, schedule


def _assert_canonical_total(after: dict, contract_value: Decimal) -> None:
    total = Decimal(after["totalScheduled"])
    if total != contract_value.quantize(Decimal("0.01")):
        raise SystemExit(
            f"HARD ASSERT falló: el plan reconstruido suma {total} y el valor contractual "
            f"es {contract_value}. No se aplica."
        )


def _rebuild_kwargs(args) -> dict:
    if not args.regular_months or not args.first_period:
        raise SystemExit("preview/apply requieren --regular-months y --first-period.")
    return {
        "regular_months": int(args.regular_months),
        "first_period": _first_period(args.first_period),
        "due_day": int(args.due_day),
        "advance_amount": Decimal(args.advance_amount) if args.advance_amount is not None else None,
        "advance_due_date": date.fromisoformat(args.advance_due_date) if args.advance_due_date else None,
        "retention_percentage": Decimal(args.retention) if args.retention is not None else None,
    }


def _run_inspect(db: Session, args) -> int:
    report = inspect(
        db,
        Filters(
            company=args.company,
            project=args.project_code,
            amount=Decimal(args.amount) if args.amount else None,
            date_from=date.fromisoformat(args.date_from) if args.date_from else None,
            date_to=date.fromisoformat(args.date_to) if args.date_to else None,
            document_number=args.document_number,
            contract_number=args.contract_number,
            bank_reference=args.reference,
        ),
    )
    _print_human(report)
    return 0


def _run_preview(db: Session, args, *, apply: bool) -> int:
    contract, schedule = _resolve_contract_schedule(db, contract_number=args.contract_number)
    kwargs = _rebuild_kwargs(args)

    if apply:
        if args.confirm != _APPLY_TOKEN:
            raise SystemExit(f"apply requiere --confirm {_APPLY_TOKEN}.")
        if not args.reason or len(args.reason.strip()) < _MIN_REASON:
            raise SystemExit(f"apply requiere --reason de al menos {_MIN_REASON} caracteres.")

    if cps.schedule_has_active_allocations(db, schedule.id):
        print(
            json.dumps(
                {
                    "mode": "apply" if apply else "preview",
                    "blocked": True,
                    "reason": (
                        "El plan tiene pagos aplicados. Requiere una enmienda formal que "
                        "preserve los períodos ya pagados (§12), no un rebuild."
                    ),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 3

    before = cps.current_schedule_snapshot(db, schedule.id)
    if apply:
        before, after = cps.apply_schedule_rebuild(db, schedule=schedule, **kwargs)
        _assert_canonical_total(after, Decimal(contract.value))
        audit_service.record(
            db,
            actor_user_id=None,
            action="contract.payment_schedule.rebuild.maintenance",
            entity_type="contract.payment_schedule",
            entity_id=schedule.id,
            company_id=schedule.company_id,
            project_id=schedule.project_id,
            before=before,
            after={**after, "reason": args.reason.strip(), "channel": "maintenance-workflow"},
            correlation_id=(args.reference or f"maintenance-{uuid.uuid4().hex[:12]}"),
        )
        db.commit()
    else:
        _contract, _rows, after = cps.build_rebuild_rows(db, schedule=schedule, **kwargs)
        _assert_canonical_total(after, Decimal(contract.value))
        db.rollback()

    print(
        json.dumps(
            {
                "mode": "apply" if apply else "preview",
                "contractNumber": contract.contract_number,
                "contractValue": str(contract.value),
                "blocked": False,
                "before": before,
                "after": after,
            },
            default=_json_default,
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--mode",
        choices=(
            "inspect",
            "preview",
            "apply",
            "reconcile-advance-preview",
            "reconcile-advance-apply",
            "finalize-reversed-invoice-preview",
            "finalize-reversed-invoice-apply",
        ),
        default="inspect",
    )
    p.add_argument("--company")
    p.add_argument("--project-code")
    p.add_argument("--contract-number")
    p.add_argument("--document-number")
    p.add_argument("--amount")
    p.add_argument("--date-from")
    p.add_argument("--date-to")
    p.add_argument("--reference")
    # términos de reconstrucción (preview/apply)
    p.add_argument("--advance-amount")
    p.add_argument("--advance-due-date")
    p.add_argument("--retention")
    p.add_argument("--regular-months", type=int)
    p.add_argument("--due-day", type=int, default=1)
    p.add_argument("--first-period")
    # reconcile-advance: corrección del anticipo duplicado (§4-§12)
    p.add_argument("--general-expense-number", help="nº de documento del GeneralExpense duplicado")
    p.add_argument("--invoice-number", help="nº de la SupplierInvoice duplicada")
    p.add_argument("--advance-account-code", help="código de la cuenta ASSET de anticipos (si no está configurada)")
    # guard de apply
    p.add_argument("--confirm")
    p.add_argument("--reason")
    return p.parse_args(argv)


def _resolve_by_number(db: Session, model, number_field: str, number: str):
    from sqlalchemy import select as _select

    return db.execute(
        _select(model).where(getattr(model, number_field) == number)
    ).scalars().first()


def _dump_asset_accounts(db: Session, company_id) -> list[dict]:
    from app.models.chart_of_accounts import Account, ChartOfAccount

    rows = db.execute(
        select(Account.code, Account.name, Account.is_postable)
        .join(ChartOfAccount, ChartOfAccount.id == Account.chart_of_account_id)
        .where(ChartOfAccount.company_id == company_id, Account.account_type == "ASSET")
        .order_by(Account.code)
    ).all()
    return [{"code": r[0], "name": r[1], "postable": bool(r[2])} for r in rows]


def _run_reconcile_advance(db: Session, args, *, apply: bool) -> int:
    from app.domain.errors import InvalidFinancialReferenceError
    from app.models.accounting import AccountingDocument
    from app.models.ap import SupplierInvoice
    from app.models.company import Company
    from app.models.treasury import GeneralExpense
    from app.services import advance_reconciliation_service as ars

    if not (args.general_expense_number and args.invoice_number and args.contract_number):
        raise SystemExit(
            "reconcile-advance requiere --general-expense-number, --invoice-number y --contract-number."
        )
    if apply:
        if args.confirm != _APPLY_TOKEN:
            raise SystemExit(f"apply requiere --confirm {_APPLY_TOKEN}.")
        if not args.reason or len(args.reason.strip()) < _MIN_REASON:
            raise SystemExit(f"apply requiere --reason de al menos {_MIN_REASON} caracteres.")

    gge_doc = _resolve_by_number(db, AccountingDocument, "document_number", args.general_expense_number)
    if gge_doc is None:
        raise SystemExit(f"No existe el asiento {args.general_expense_number!r}")
    gge = db.execute(
        select(GeneralExpense).where(GeneralExpense.accounting_document_id == gge_doc.id)
    ).scalars().first()
    if gge is None:
        raise SystemExit(f"{args.general_expense_number} no corresponde a un GeneralExpense")
    invoice = _resolve_by_number(db, SupplierInvoice, "invoice_number", args.invoice_number)
    if invoice is None:
        raise SystemExit(f"No existe la factura {args.invoice_number!r}")

    try:
        result = ars.reconcile_duplicated_advance(
            db,
            general_expense_id=gge.id,
            supplier_invoice_id=invoice.id,
            contract_number=args.contract_number,
            advance_account_code=args.advance_account_code,
            reason=(args.reason or "PREVIEW").strip(),
            correlation_id=(args.reference or f"cierre-l50k-{uuid.uuid4().hex[:10]}"),
            commit=apply,
        )
    except InvalidFinancialReferenceError as exc:
        db.rollback()
        payload = {"mode": args.mode, "blocked": True, "reason": str(exc)}
        if "cuenta ASSET de anticipos" in str(exc):
            payload["companyAssetAccounts"] = _dump_asset_accounts(db, gge.company_id)
            payload["companySupplierAdvanceAccountId"] = (
                str(db.get(Company, gge.company_id).supplier_advance_account_id)
                if db.get(Company, gge.company_id).supplier_advance_account_id
                else None
            )
            payload["hint"] = (
                "Pasa --advance-account-code con el código de una cuenta ASSET postable "
                "de anticipos, o configúrala en Company Settings."
            )
        print(json.dumps(payload, default=_json_default, indent=2, ensure_ascii=False))
        return 3
    if not apply:
        db.rollback()
    print(
        json.dumps(
            {"mode": "reconcile-advance-apply" if apply else "reconcile-advance-preview", **result},
            default=_json_default,
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _run_finalize_reversed_invoice(db: Session, args, *, apply: bool) -> int:
    """Cierra una factura cuyo accrual ya está REVERSED pero quedó en APPROVED.

    Ocurre cuando el accrual se revirtió desde un proceso que no tenía
    registrado el hook de reversión ``supplier_invoice`` (p. ej. una versión
    anterior de este runner). Sólo transiciona a CANCELLED; no toca el GL.
    """
    from app.models.accounting import AccountingDocument
    from app.models.ap import SupplierInvoice

    if not args.invoice_number:
        raise SystemExit("finalize-reversed-invoice requiere --invoice-number.")
    if apply:
        if args.confirm != _APPLY_TOKEN:
            raise SystemExit(f"apply requiere --confirm {_APPLY_TOKEN}.")
        if not args.reason or len(args.reason.strip()) < _MIN_REASON:
            raise SystemExit(f"apply requiere --reason de al menos {_MIN_REASON} caracteres.")

    invoice = _resolve_by_number(db, SupplierInvoice, "invoice_number", args.invoice_number)
    if invoice is None:
        raise SystemExit(f"No existe la factura {args.invoice_number!r}")

    accrual = (
        db.get(AccountingDocument, invoice.accrual_document_id)
        if invoice.accrual_document_id
        else None
    )
    blocked = None
    if invoice.status != "APPROVED":
        blocked = f"la factura está en estado {invoice.status}, no APPROVED"
    elif invoice.amount_paid and invoice.amount_paid > 0:
        blocked = "la factura tiene pagos registrados"
    elif accrual is None:
        blocked = "la factura no tiene accrual contabilizado"
    elif accrual.status != "REVERSED":
        blocked = f"el accrual está en estado {accrual.status}, no REVERSED"

    payload = {
        "mode": args.mode,
        "invoiceNumber": invoice.invoice_number,
        "before": {"invoiceStatus": invoice.status, "accrualStatus": accrual.status if accrual else None},
    }
    if blocked is not None:
        payload.update({"blocked": True, "reason": blocked})
        print(json.dumps(payload, default=_json_default, indent=2, ensure_ascii=False))
        return 3

    if apply:
        before_status = invoice.status
        invoice.status = "CANCELLED"
        audit_service.record(
            db,
            actor_user_id=None,
            action="ap.supplier_invoice.finalize_reversed",
            entity_type="ap.supplier_invoice",
            entity_id=invoice.id,
            company_id=invoice.company_id,
            project_id=invoice.project_id,
            before={"status": before_status},
            after={"status": "CANCELLED", "reason": args.reason.strip(), "channel": "maintenance-workflow"},
            correlation_id=(args.reference or f"finalize-reversed-{uuid.uuid4().hex[:12]}"),
        )
        db.commit()
        payload["after"] = {"invoiceStatus": "CANCELLED", "accrualStatus": accrual.status}
    else:
        db.rollback()
        payload["after"] = {"invoiceStatus": "CANCELLED (preview)", "accrualStatus": accrual.status}
    payload["blocked"] = False
    print(json.dumps(payload, default=_json_default, indent=2, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    register_default_reversal_hooks()
    db = SessionLocal()
    try:
        if args.mode == "inspect":
            return _run_inspect(db, args)
        if args.mode.startswith("finalize-reversed-invoice"):
            return _run_finalize_reversed_invoice(db, args, apply=args.mode.endswith("apply"))
        if args.mode.startswith("reconcile-advance"):
            return _run_reconcile_advance(db, args, apply=args.mode.endswith("apply"))
        if not args.contract_number:
            raise SystemExit("preview/apply requieren --contract-number.")
        return _run_preview(db, args, apply=(args.mode == "apply"))
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
