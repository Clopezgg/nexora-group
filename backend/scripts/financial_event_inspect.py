"""Forensic inspector for a financial business event (ORDEN MAESTRA §4/§5/§6/§27).

READ-ONLY. This tool never writes to the database. It answers "what operations
produced this money movement?" by pulling every related record — across
Treasury, AP, the contractual subledger, the General Ledger, evidence, vouchers
and the audit trail — for a set of *generic* filters. Nothing is hardcoded to a
particular contract number or amount; every selector is a CLI argument.

Usage (from ``backend/``, with ``DATABASE_URL`` pointing at the target DB)::

    python -m scripts.financial_event_inspect --company "NEXORA GROUP" --amount 50000
    python -m scripts.financial_event_inspect --contract-number 10101960
    python -m scripts.financial_event_inspect --project-code 3201 --date-from 2026-08-01
    python -m scripts.financial_event_inspect --document-number 2020485218 --json

The default (and only) mode is ``--dry-run``: the flag is accepted for interface
symmetry with the repair tooling but this script has no write path at all.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.accounting import AccountingDocument, AccountingSourceLink, JournalLine
from app.models.ap import SupplierInvoice, SupplierPayment
from app.models.audit import AuditLog
from app.models.chart_of_accounts import Account
from app.models.company import Company
from app.models.contract_payment import (
    ContractPaymentAllocation,
    ContractPaymentInstallment,
    ContractPaymentSchedule,
)
from app.models.evidence import Evidence
from app.models.project import Project
from app.models.supplier import Supplier, SupplierContract
from app.models.treasury import (
    GeneralExpense,
    Remittance,
    TreasuryAccount,
    TreasuryTransfer,
)
from app.models.voucher_issuance import VoucherIssuance


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


@dataclass
class Filters:
    company: str | None = None
    project: str | None = None
    amount: Decimal | None = None
    amount_tolerance: Decimal = Decimal("0.01")
    date_from: date | None = None
    date_to: date | None = None
    document_number: str | None = None
    contract_number: str | None = None
    bank_reference: str | None = None
    supplier: str | None = None


@dataclass
class Report:
    filters: dict = field(default_factory=dict)
    resolved: dict = field(default_factory=dict)
    sections: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Resolution helpers                                                           #
# --------------------------------------------------------------------------- #

def _maybe_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _resolve_company(db: Session, token: str | None) -> Company | None:
    if not token:
        return None
    as_id = _maybe_uuid(token)
    if as_id is not None:
        return db.get(Company, as_id)
    like = f"%{token.strip()}%"
    return db.execute(
        select(Company).where(
            or_(
                Company.name.ilike(like),
                Company.legal_name.ilike(like),
                Company.trade_name.ilike(like),
                Company.code.ilike(like),
            )
        )
    ).scalars().first()


def _resolve_project(db: Session, token: str | None, company_id: uuid.UUID | None) -> Project | None:
    if not token:
        return None
    as_id = _maybe_uuid(token)
    stmt = select(Project)
    if as_id is not None:
        stmt = stmt.where(Project.id == as_id)
    else:
        like = f"%{token.strip()}%"
        stmt = stmt.where(or_(Project.code.ilike(like), Project.name.ilike(like)))
    if company_id is not None:
        stmt = stmt.where(Project.company_id == company_id)
    return db.execute(stmt).scalars().first()


def _resolve_suppliers(db: Session, token: str | None, company_id: uuid.UUID | None) -> list[Supplier]:
    if not token:
        return []
    as_id = _maybe_uuid(token)
    stmt = select(Supplier)
    if as_id is not None:
        stmt = stmt.where(Supplier.id == as_id)
    else:
        like = f"%{token.strip()}%"
        stmt = stmt.where(or_(Supplier.legal_name.ilike(like), Supplier.trade_name.ilike(like), Supplier.tax_id.ilike(like)))
    if company_id is not None:
        stmt = stmt.where(Supplier.company_id == company_id)
    return list(db.execute(stmt).scalars().all())


# --------------------------------------------------------------------------- #
# Amount / date predicates                                                     #
# --------------------------------------------------------------------------- #

def _amount_matches(value, target: Decimal | None, tol: Decimal) -> bool:
    if target is None or value is None:
        return target is None
    try:
        return abs(Decimal(value) - target) <= tol
    except (InvalidOperation, TypeError):
        return False


def _in_range(value: date | datetime | None, lo: date | None, hi: date | None) -> bool:
    if value is None:
        return lo is None and hi is None
    if isinstance(value, datetime):
        value = value.date()
    if lo is not None and value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


# --------------------------------------------------------------------------- #
# Serialization                                                                #
# --------------------------------------------------------------------------- #

def _account_label(db: Session, account_id) -> str:
    account = db.get(Account, account_id)
    if account is None:
        return str(account_id)
    return f"{account.code} {account.name} [{account.account_type}]"


def _row(obj, fields: list[str]) -> dict:
    return {f: getattr(obj, f, None) for f in fields}


# --------------------------------------------------------------------------- #
# Collectors                                                                   #
# --------------------------------------------------------------------------- #

def _collect_general_expenses(db: Session, f: Filters, company_id, project_ids) -> list[dict]:
    stmt = select(GeneralExpense)
    if company_id is not None:
        stmt = stmt.where(GeneralExpense.company_id == company_id)
    out = []
    for ge in db.execute(stmt).scalars().all():
        doc = db.get(AccountingDocument, ge.accounting_document_id)
        doc_project = doc.project_id if doc is not None else None
        if project_ids and doc_project not in project_ids:
            continue
        if not _amount_matches(ge.amount, f.amount, f.amount_tolerance):
            continue
        if not _in_range(ge.expense_date, f.date_from, f.date_to):
            continue
        if f.document_number and (doc is None or f.document_number not in (doc.document_number or "")):
            continue
        out.append(
            {
                **_row(ge, ["id", "amount", "currency_code", "category", "expense_date", "description"]),
                "expense_account": _account_label(db, ge.expense_account_id),
                "treasury_account_id": ge.treasury_account_id,
                "accounting_document_id": ge.accounting_document_id,
                "accounting_document_number": doc.document_number if doc else None,
                "accounting_scope": doc.scope if doc else None,
                "accounting_project_id": doc_project,
                "effective_date": doc.effective_date if doc else None,
            }
        )
    return out


def _collect_supplier_invoices(db: Session, f: Filters, company_id, project_ids, supplier_ids) -> list[dict]:
    stmt = select(SupplierInvoice)
    if company_id is not None:
        stmt = stmt.where(SupplierInvoice.company_id == company_id)
    if project_ids:
        stmt = stmt.where(SupplierInvoice.project_id.in_(project_ids))
    if supplier_ids:
        stmt = stmt.where(SupplierInvoice.supplier_id.in_(supplier_ids))
    out = []
    for inv in db.execute(stmt).scalars().all():
        total = (inv.amount or Decimal(0)) + (inv.tax_amount or Decimal(0))
        if not (
            _amount_matches(inv.amount, f.amount, f.amount_tolerance)
            or _amount_matches(total, f.amount, f.amount_tolerance)
        ):
            continue
        if not _in_range(inv.invoice_date, f.date_from, f.date_to):
            continue
        if f.document_number and f.document_number not in (inv.invoice_number or ""):
            continue
        supplier = db.get(Supplier, inv.supplier_id)
        expense_account = db.get(Account, inv.expense_account_id)
        out.append(
            {
                **_row(
                    inv,
                    [
                        "id", "invoice_number", "scope", "project_id", "amount", "tax_amount",
                        "amount_paid", "invoice_date", "due_date", "status", "description",
                        "accrual_document_id", "supplier_contract_id",
                    ],
                ),
                "supplier": supplier.legal_name if supplier else str(inv.supplier_id),
                "supplier_party_role": supplier.party_role if supplier else None,
                "expense_account": _account_label(db, inv.expense_account_id),
                "expense_account_type": expense_account.account_type if expense_account else None,
                "is_prepayment_debit": bool(expense_account and expense_account.account_type == "ASSET"),
            }
        )
    return out


def _collect_supplier_payments(db: Session, f: Filters, company_id, invoice_ids) -> list[dict]:
    stmt = select(SupplierPayment)
    if invoice_ids:
        stmt = stmt.where(SupplierPayment.supplier_invoice_id.in_(invoice_ids))
    out = []
    for pay in db.execute(stmt).scalars().all():
        inv = db.get(SupplierInvoice, pay.supplier_invoice_id)
        if company_id is not None and inv is not None and inv.company_id != company_id:
            continue
        if not invoice_ids and not _amount_matches(pay.amount, f.amount, f.amount_tolerance):
            continue
        if not _in_range(pay.payment_date, f.date_from, f.date_to):
            continue
        if f.bank_reference and f.bank_reference not in (pay.bank_transaction_reference or ""):
            continue
        allocations = db.execute(
            select(ContractPaymentAllocation).where(
                ContractPaymentAllocation.supplier_payment_id == pay.id
            )
        ).scalars().all()
        out.append(
            {
                **_row(
                    pay,
                    [
                        "id", "supplier_invoice_id", "treasury_account_id", "amount",
                        "payment_date", "accounting_document_id", "reversal_accounting_document_id",
                        "reversed_at", "reversal_reason", "bank_transaction_reference",
                        "payment_observations",
                    ],
                ),
                "invoice_number": inv.invoice_number if inv else None,
                "contract_allocations": [
                    {
                        "installment_id": a.installment_id,
                        "amount_applied": a.amount_applied,
                        "reversed_at": a.reversed_at,
                    }
                    for a in allocations
                ],
            }
        )
    return out


def _collect_contract(db: Session, f: Filters, company_id, project_ids) -> list[dict]:
    stmt = select(SupplierContract)
    if company_id is not None:
        stmt = stmt.where(SupplierContract.company_id == company_id)
    if f.contract_number:
        stmt = stmt.where(SupplierContract.contract_number.ilike(f"%{f.contract_number}%"))
    if project_ids:
        stmt = stmt.where(SupplierContract.project_id.in_(project_ids))
    out = []
    for c in db.execute(stmt).scalars().all():
        schedule = db.execute(
            select(ContractPaymentSchedule).where(
                ContractPaymentSchedule.supplier_contract_id == c.id
            )
        ).scalars().first()
        installments = []
        if schedule is not None:
            installments = db.execute(
                select(ContractPaymentInstallment)
                .where(ContractPaymentInstallment.schedule_id == schedule.id)
                .order_by(ContractPaymentInstallment.sequence)
            ).scalars().all()
        supplier = db.get(Supplier, c.supplier_id)
        paid = Decimal(0)
        inst_rows = []
        for inst in installments:
            allocs = db.execute(
                select(ContractPaymentAllocation).where(
                    ContractPaymentAllocation.installment_id == inst.id,
                    ContractPaymentAllocation.reversed_at.is_(None),
                )
            ).scalars().all()
            inst_paid = sum((a.amount_applied for a in allocs), Decimal(0))
            paid += inst_paid
            inst_rows.append(
                {
                    **_row(
                        inst,
                        [
                            "id", "sequence", "installment_kind", "period_year", "period_month",
                            "due_date", "scheduled_amount", "retention_amount", "net_due", "status",
                        ],
                    ),
                    "paid_active": inst_paid,
                }
            )
        out.append(
            {
                "contract": _row(
                    c,
                    [
                        "id", "contract_number", "contract_category", "value", "currency_code",
                        "start_date", "end_date", "advance_percentage", "advance_amount",
                        "advance_due_date", "retention_percentage", "payment_terms_type", "status",
                        "project_id",
                    ],
                ),
                "supplier": supplier.legal_name if supplier else str(c.supplier_id),
                "schedule": _row(
                    schedule,
                    ["id", "schedule_type", "due_day", "start_period", "end_period", "total_scheduled", "status"],
                ) if schedule else None,
                "installments": inst_rows,
                "derived_paid_active": paid,
                "derived_balance": (c.value or Decimal(0)) - paid,
            }
        )
    return out


def _collect_accounting(db: Session, f: Filters, company_id, project_ids) -> list[dict]:
    stmt = select(AccountingDocument)
    if company_id is not None:
        stmt = stmt.where(AccountingDocument.company_id == company_id)
    if f.document_number:
        stmt = stmt.where(AccountingDocument.document_number.ilike(f"%{f.document_number}%"))
    if project_ids:
        stmt = stmt.where(
            or_(
                AccountingDocument.project_id.in_(project_ids),
                AccountingDocument.project_id.is_(None),
            )
        )
    out = []
    for doc in db.execute(stmt).scalars().all():
        lines = db.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == doc.id)
        ).scalars().all()
        doc_total = sum((ln.debit_amount for ln in lines), Decimal(0))
        matches_amount = f.amount is None or _amount_matches(doc_total, f.amount, f.amount_tolerance) or any(
            _amount_matches(ln.debit_amount, f.amount, f.amount_tolerance)
            or _amount_matches(ln.credit_amount, f.amount, f.amount_tolerance)
            for ln in lines
        )
        in_range = _in_range(doc.effective_date, f.date_from, f.date_to) or _in_range(
            doc.posted_at, f.date_from, f.date_to
        )
        if not f.document_number and not (matches_amount and in_range):
            continue
        source_links = db.execute(
            select(AccountingSourceLink).where(
                AccountingSourceLink.accounting_document_id == doc.id
            )
        ).scalars().all()
        out.append(
            {
                **_row(
                    doc,
                    [
                        "id", "document_type_code", "document_number", "scope", "project_id",
                        "currency_code", "status", "description", "effective_date", "posted_at",
                        "reversed_document_id", "reversal_reason",
                    ],
                ),
                "total_debit": doc_total,
                "lines": [
                    {
                        "account": _account_label(db, ln.account_id),
                        "debit_amount": ln.debit_amount,
                        "credit_amount": ln.credit_amount,
                        "project_id": ln.project_id,
                        "description": ln.description,
                    }
                    for ln in lines
                ],
                "source_links": [
                    {"source_type": sl.source_type, "source_id": sl.source_id} for sl in source_links
                ],
            }
        )
    return out


def _collect_treasury_context(db: Session, f: Filters, company_id, project_ids) -> dict:
    remittances = []
    r_stmt = select(Remittance)
    if company_id is not None:
        r_stmt = r_stmt.where(Remittance.company_id == company_id)
    for rem in db.execute(r_stmt).scalars().all():
        if not _amount_matches(rem.original_amount, f.amount, f.amount_tolerance) and not _amount_matches(
            rem.base_amount, f.amount, f.amount_tolerance
        ):
            continue
        if not _in_range(rem.remittance_date, f.date_from, f.date_to):
            continue
        if f.bank_reference and f.bank_reference not in (rem.reference or ""):
            continue
        remittances.append(
            _row(
                rem,
                ["id", "sender", "provider", "channel", "original_amount", "base_amount",
                 "reference", "remittance_date", "accounting_document_id"],
            )
        )
    transfers = []
    for tr in db.execute(select(TreasuryTransfer)).scalars().all():
        if company_id is not None and tr.company_id != company_id:
            continue
        if not _amount_matches(tr.amount, f.amount, f.amount_tolerance):
            continue
        if not _in_range(tr.transfer_date, f.date_from, f.date_to):
            continue
        transfers.append(
            _row(tr, ["id", "amount", "currency_code", "transfer_date", "notes", "accounting_document_id"])
        )
    accounts = []
    a_stmt = select(TreasuryAccount)
    if company_id is not None:
        a_stmt = a_stmt.where(TreasuryAccount.company_id == company_id)
    for acc in db.execute(a_stmt).scalars().all():
        accounts.append(_row(acc, ["id", "name", "currency_code", "gl_account_id"]))
    return {"remittances": remittances, "transfers": transfers, "treasury_accounts": accounts}


def _collect_vouchers_evidence_audit(db: Session, doc_ids, company_id, project_ids) -> dict:
    vouchers = []
    if doc_ids:
        for v in db.execute(
            select(VoucherIssuance).where(VoucherIssuance.accounting_document_id.in_(doc_ids))
        ).scalars().all():
            vouchers.append(
                _row(
                    v,
                    ["id", "document_number", "issued_on", "beneficiary_name_snapshot",
                     "amount_snapshot", "currency_code_snapshot", "contract_number_snapshot",
                     "contract_value_snapshot", "paid_accumulated_snapshot",
                     "contract_balance_snapshot", "verification_code", "status"],
                )
            )
    audits = []
    au_stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)
    if company_id is not None:
        au_stmt = au_stmt.where(AuditLog.company_id == company_id)
    if project_ids:
        au_stmt = au_stmt.where(
            or_(AuditLog.project_id.in_(project_ids), AuditLog.project_id.is_(None))
        )
    for a in db.execute(au_stmt).scalars().all():
        audits.append(_row(a, ["id", "action", "entity_type", "entity_id", "correlation_id", "created_at"]))
    evidence = []
    ev_stmt = select(Evidence)
    if company_id is not None:
        ev_stmt = ev_stmt.where(Evidence.company_id == company_id)
    for e in db.execute(ev_stmt.limit(200)).scalars().all():
        evidence.append(_row(e, ["id", "original_filename", "category", "entity_type", "entity_id", "content_hash"]))
    return {"vouchers": vouchers, "audit_logs": audits, "evidence": evidence}


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #

def inspect(db: Session, f: Filters) -> Report:
    report = Report(filters={k: v for k, v in vars(f).items() if v not in (None, "")})

    company = _resolve_company(db, f.company)
    company_id = company.id if company else None
    if f.company and company is None:
        report.notes.append(f"No se resolvió ninguna compañía para {f.company!r}")

    projects: list[Project] = []
    if f.project:
        project = _resolve_project(db, f.project, company_id)
        if project is not None:
            projects = [project]
            if company_id is None:
                company_id = project.company_id
                company = db.get(Company, company_id)
        else:
            report.notes.append(f"No se resolvió ningún proyecto para {f.project!r}")
    project_ids = [p.id for p in projects]

    suppliers = _resolve_suppliers(db, f.supplier, company_id)
    supplier_ids = [s.id for s in suppliers]

    report.resolved = {
        "company": {"id": company.id, "name": company.name} if company else None,
        "projects": [{"id": p.id, "code": p.code, "name": p.name} for p in projects],
        "suppliers": [{"id": s.id, "name": s.legal_name, "party_role": s.party_role} for s in suppliers],
    }

    contracts = _collect_contract(db, f, company_id, project_ids)
    contract_ids = [c["contract"]["id"] for c in contracts]

    general_expenses = _collect_general_expenses(db, f, company_id, project_ids)
    invoices = _collect_supplier_invoices(db, f, company_id, project_ids, supplier_ids)
    # widen invoice set with contract-linked invoices even if amount differs
    if contract_ids:
        extra = db.execute(
            select(SupplierInvoice).where(SupplierInvoice.supplier_contract_id.in_(contract_ids))
        ).scalars().all()
        known = {i["id"] for i in invoices}
        for inv in extra:
            if inv.id in known:
                continue
            supplier = db.get(Supplier, inv.supplier_id)
            expense_account = db.get(Account, inv.expense_account_id)
            invoices.append(
                {
                    **_row(
                        inv,
                        ["id", "invoice_number", "scope", "project_id", "amount", "tax_amount",
                         "amount_paid", "invoice_date", "due_date", "status", "description",
                         "accrual_document_id", "supplier_contract_id"],
                    ),
                    "supplier": supplier.legal_name if supplier else str(inv.supplier_id),
                    "supplier_party_role": supplier.party_role if supplier else None,
                    "expense_account": _account_label(db, inv.expense_account_id),
                    "expense_account_type": expense_account.account_type if expense_account else None,
                    "is_prepayment_debit": bool(expense_account and expense_account.account_type == "ASSET"),
                    "_via": "contract-link",
                }
            )
    invoice_ids = [i["id"] for i in invoices]

    payments = _collect_supplier_payments(db, f, company_id, invoice_ids)
    accounting = _collect_accounting(db, f, company_id, project_ids)
    treasury = _collect_treasury_context(db, f, company_id, project_ids)

    doc_ids = set()
    for coll in (general_expenses, payments):
        for row in coll:
            if row.get("accounting_document_id"):
                doc_ids.add(row["accounting_document_id"])
    for row in invoices:
        if row.get("accrual_document_id"):
            doc_ids.add(row["accrual_document_id"])
    for row in accounting:
        doc_ids.add(row["id"])
    for row in treasury["remittances"] + treasury["transfers"]:
        if row.get("accounting_document_id"):
            doc_ids.add(row["accounting_document_id"])

    vea = _collect_vouchers_evidence_audit(db, list(doc_ids), company_id, project_ids)

    report.sections = {
        "contracts": contracts,
        "general_expenses": general_expenses,
        "supplier_invoices": invoices,
        "supplier_payments": payments,
        "accounting_documents": accounting,
        "treasury": treasury,
        "vouchers": vea["vouchers"],
        "evidence": vea["evidence"],
        "audit_logs": vea["audit_logs"],
    }

    # --- Duplicate-event heuristic (§4) --------------------------------------
    if f.amount is not None:
        cash_out = [g for g in general_expenses] + [
            p for p in payments if not p.get("reversed_at")
        ]
        accruals = [i for i in invoices if i["status"] not in ("DRAFT", "REVIEW", "CANCELLED")]
        if general_expenses and accruals:
            report.notes.append(
                "POSIBLE DOBLE CONTEO: existe GeneralExpense y SupplierInvoice por un importe "
                "compatible para el mismo periodo. Verificar si son el mismo hecho económico "
                "registrado dos veces (§4/§11)."
            )
        prepay_invoices = [
            i for i in invoices
            if i.get("is_prepayment_debit") and i["status"] != "CANCELLED"
        ]
        if prepay_invoices:
            estados = sorted({i["status"] for i in prepay_invoices})
            report.notes.append(
                "Hay factura(s) de proveedor cuyo débito es una cuenta ASSET (anticipo/prepago) "
                f"[estado(s): {', '.join(estados)}]: NO deben contarse como costo real del "
                "proyecto hasta su aplicación (§13/§15)."
            )
        if len(cash_out) > 1:
            report.notes.append(
                f"{len(cash_out)} salidas de caja compatibles con el importe: confirmar que el "
                "dinero salió UNA sola vez (§11/§12)."
            )

    return report


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def _print_human(report: Report) -> None:
    def h(title):
        print(f"\n{'=' * 4} {title} {'=' * (72 - len(title))}")

    h("FILTROS")
    print(json.dumps(report.filters, default=_json_default, indent=2, ensure_ascii=False))
    h("RESUELTO")
    print(json.dumps(report.resolved, default=_json_default, indent=2, ensure_ascii=False))

    for name, rows in report.sections.items():
        h(name.upper())
        print(json.dumps(rows, default=_json_default, indent=2, ensure_ascii=False))

    h("OBSERVACIONES FORENSES")
    if report.notes:
        for note in report.notes:
            print(f" - {note}")
    else:
        print(" (sin observaciones automáticas)")


def _parse_args(argv: list[str]) -> tuple[Filters, bool]:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--company")
    p.add_argument("--project", help="id, código o nombre (parcial)")
    p.add_argument("--project-code", dest="project", help="alias de --project")
    p.add_argument("--amount", type=str)
    p.add_argument("--amount-tolerance", type=str, default="0.01")
    p.add_argument("--date-from", type=str)
    p.add_argument("--date-to", type=str)
    p.add_argument("--document-number")
    p.add_argument("--contract-number")
    p.add_argument("--bank-reference")
    p.add_argument("--supplier", help="proveedor/contratista: id, razón social o RTN (parcial)")
    p.add_argument("--json", action="store_true", help="salida JSON en vez de texto")
    p.add_argument("--dry-run", action="store_true", default=True, help="(no-op) esta herramienta es de solo lectura")
    args = p.parse_args(argv)

    def _d(v):
        return date.fromisoformat(v) if v else None

    filters = Filters(
        company=args.company,
        project=args.project,
        amount=Decimal(args.amount) if args.amount else None,
        amount_tolerance=Decimal(args.amount_tolerance),
        date_from=_d(args.date_from),
        date_to=_d(args.date_to),
        document_number=args.document_number,
        contract_number=args.contract_number,
        bank_reference=args.bank_reference,
        supplier=args.supplier,
    )
    return filters, args.json


def main(argv: list[str] | None = None) -> int:
    filters, as_json = _parse_args(argv if argv is not None else sys.argv[1:])
    if not any(
        v not in (None, "") for k, v in vars(filters).items() if k != "amount_tolerance"
    ):
        print("Se requiere al menos un filtro (--company, --contract-number, --amount, ...).", file=sys.stderr)
        return 2
    db = SessionLocal()
    try:
        report = inspect(db, filters)
    finally:
        db.close()
    if as_json:
        print(
            json.dumps(
                {
                    "filters": report.filters,
                    "resolved": report.resolved,
                    "sections": report.sections,
                    "notes": report.notes,
                },
                default=_json_default,
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        _print_human(report)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
