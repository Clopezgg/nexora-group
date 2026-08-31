"""Exception Center (orden maestra FINAL, Phase 5). "Exception Zero": una
lista única y accionable de todo lo que está mal a nivel financiero/dato en
una compañía. Cada excepción se deriva de la base de datos (sin cifras
inventadas) y trae una acción sugerida + ruta de resolución.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_time import business_today
from app.models.ap import SupplierInvoice
from app.models.approval_request import ApprovalRequest
from app.models.ar import CustomerInvoice
from app.models.company import Company
from app.models.fiscal import FiscalPeriod
from app.models.treasury import BankStatement, BankStatementLine, TreasuryAccount
from app.services import subledger_reconciliation_service

_AP_OPEN = ("APPROVED", "SCHEDULED", "PARTIALLY_PAID")
_AR_OPEN = ("APPROVED", "PARTIALLY_COLLECTED")
_STALE_APPROVAL_DAYS = 7


@dataclass(frozen=True)
class Exception_:
    code: str
    severity: str  # "info" | "warning" | "critical"
    title: str
    detail: str
    count: int
    suggested_action: str
    route: str | None = None


def list_exceptions(db: Session, *, company_id, as_of: date | None = None) -> list[Exception_]:
    as_of = as_of or business_today()
    out: list[Exception_] = []

    # 1. Subledger <-> GL descuadres.
    recon = subledger_reconciliation_service.reconcile(db, company_id=company_id)
    unreconciled = [line for line in recon if not line.reconciled]
    if unreconciled:
        names = ", ".join(line.subledger for line in unreconciled)
        out.append(
            Exception_(
                code="SUBLEDGER_GL_MISMATCH",
                severity="critical",
                title="Subledger descuadrado contra el GL",
                detail=f"Descuadre en: {names}.",
                count=len(unreconciled),
                suggested_action="Revisar los movimientos del subledger vs. su cuenta de control.",
                route="/finanzas/conciliacion-subledger",
            )
        )

    # 2. Líneas bancarias sin conciliar (de esta compañía).
    unmatched = db.execute(
        select(func.count(BankStatementLine.id))
        .join(BankStatement, BankStatement.id == BankStatementLine.bank_statement_id)
        .join(TreasuryAccount, TreasuryAccount.id == BankStatement.treasury_account_id)
        .where(TreasuryAccount.company_id == company_id)
        .where(BankStatementLine.status == "UNMATCHED")
    ).scalar_one()
    if unmatched:
        out.append(
            Exception_(
                code="UNMATCHED_BANK_LINES",
                severity="warning",
                title="Líneas bancarias sin conciliar",
                detail=f"{unmatched} línea(s) de estado de cuenta en estado UNMATCHED.",
                count=int(unmatched),
                suggested_action="Conciliar o excluir las líneas en la conciliación bancaria.",
                route="/finanzas/conciliacion",
            )
        )

    # 3. AP vencida.
    ap_rows = db.execute(
        select(SupplierInvoice.due_date, SupplierInvoice.amount, SupplierInvoice.tax_amount, SupplierInvoice.amount_paid)
        .where(SupplierInvoice.company_id == company_id)
        .where(SupplierInvoice.status.in_(_AP_OPEN))
    ).all()
    ap_overdue = [r for r in ap_rows if (r[1] + r[2] - r[3]) > 0 and r[0] < as_of]
    if ap_overdue:
        total = sum((r[1] + r[2] - r[3] for r in ap_overdue), Decimal("0"))
        out.append(
            Exception_(
                code="AP_OVERDUE",
                severity="warning",
                title="Facturas de proveedor vencidas",
                detail=f"{len(ap_overdue)} factura(s) con saldo pendiente y vencimiento anterior a hoy ({total}).",
                count=len(ap_overdue),
                suggested_action="Programar pago o renegociar el vencimiento.",
                route="/finanzas/cuentas-por-pagar",
            )
        )

    # 4. AR vencida.
    ar_rows = db.execute(
        select(CustomerInvoice.due_date, CustomerInvoice.amount, CustomerInvoice.amount_collected)
        .where(CustomerInvoice.company_id == company_id)
        .where(CustomerInvoice.status.in_(_AR_OPEN))
    ).all()
    ar_overdue = [r for r in ar_rows if (r[1] - r[2]) > 0 and r[0] < as_of]
    if ar_overdue:
        total = sum((r[1] - r[2] for r in ar_overdue), Decimal("0"))
        out.append(
            Exception_(
                code="AR_OVERDUE",
                severity="warning",
                title="Facturas de cliente vencidas",
                detail=f"{len(ar_overdue)} factura(s) por cobrar con vencimiento anterior a hoy ({total}).",
                count=len(ar_overdue),
                suggested_action="Gestionar cobro con el cliente.",
                route="/finanzas/cuentas-por-cobrar",
            )
        )

    # 5. Aprobaciones estancadas.
    cutoff = datetime.now(timezone.utc) - timedelta(days=_STALE_APPROVAL_DAYS)
    stale = db.execute(
        select(func.count(ApprovalRequest.id))
        .where(ApprovalRequest.company_id == company_id)
        .where(ApprovalRequest.status == "PENDING")
        .where(ApprovalRequest.created_at < cutoff)
    ).scalar_one()
    if stale:
        out.append(
            Exception_(
                code="STALE_APPROVALS",
                severity="warning",
                title="Aprobaciones estancadas",
                detail=f"{stale} solicitud(es) de aprobación pendientes por más de {_STALE_APPROVAL_DAYS} días.",
                count=int(stale),
                suggested_action="Escalar o reasignar la aprobación.",
                route="/inicio/aprobaciones",
            )
        )

    # 6. Período fiscal no configurado para hoy.
    period = db.execute(
        select(FiscalPeriod.id)
        .where(FiscalPeriod.company_id == company_id)
        .where(FiscalPeriod.start_date <= as_of)
        .where(FiscalPeriod.end_date >= as_of)
    ).first()
    if period is None:
        out.append(
            Exception_(
                code="FISCAL_PERIOD_MISSING",
                severity="critical",
                title="Período fiscal no configurado",
                detail="No hay un período fiscal que cubra la fecha de hoy. Los postings quedarán bloqueados.",
                count=1,
                suggested_action="Crear el año fiscal y generar sus períodos mensuales.",
                route="/control/configuracion",
            )
        )

    # 7. Números de factura de proveedor duplicados.
    dup_rows = db.execute(
        select(
            SupplierInvoice.supplier_id,
            SupplierInvoice.invoice_number,
            func.count(SupplierInvoice.id).label("n"),
        )
        .where(SupplierInvoice.company_id == company_id)
        .where(SupplierInvoice.status != "CANCELLED")
        .group_by(SupplierInvoice.supplier_id, SupplierInvoice.invoice_number)
        .having(func.count(SupplierInvoice.id) > 1)
    ).all()
    if dup_rows:
        out.append(
            Exception_(
                code="DUPLICATE_SUPPLIER_INVOICE",
                severity="critical",
                title="Facturas de proveedor duplicadas",
                detail=f"{len(dup_rows)} combinación(es) (proveedor, número de factura) registradas más de una vez.",
                count=len(dup_rows),
                suggested_action="Anular la factura duplicada; conservar solo la original.",
                route="/finanzas/cuentas-por-pagar",
            )
        )

    # 8. Pagador de comprobantes sin fijar.
    company = db.get(Company, company_id)
    if company is not None and not company.voucher_payer_name:
        out.append(
            Exception_(
                code="VOUCHER_PAYER_UNSET",
                severity="info",
                title="Pagador de comprobantes sin configurar",
                detail="Los comprobantes usarán el nombre de la compañía como pagador hasta que se fije.",
                count=1,
                suggested_action="Fijar el pagador en Configuración → Perfil de la compañía.",
                route="/control/configuracion",
            )
        )

    return out
