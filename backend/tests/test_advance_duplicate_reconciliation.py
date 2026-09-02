"""Reconciliación de un anticipo contractual registrado por duplicado
(ORDEN MAESTRA DE CIERRE §1-§12, §18).

Reproduce el caso productivo de los L50,000: GeneralExpense (salida de caja
real, Debit gasto/Credit Tesorería) + SupplierInvoice por el mismo anticipo
(Debit gasto/Credit CxP). La corrección debe terminar con: caja −50k UNA vez,
GL cost sin doble reconocimiento, AP sin obligación duplicada, contrato con el
anticipo pagado y saldo 1,450,000.
"""

from decimal import Decimal

from app.models.company import Company
from app.services import advance_reconciliation_service as ars
from app.services import contract_payment_service as cps
from tests.helpers import create_account, create_company, create_supplier, create_treasury_account, login_admin


def _bank_balance(client, company_id, ta_id):
    accounts = client.get(f"/api/treasury/accounts?companyId={company_id}").json()
    return Decimal(next(a["balance"] for a in accounts if a["id"] == ta_id))


def _setup(client, db_session):
    login_admin(client)
    company = create_company(client, name="L50k Recon Co")
    supplier = create_supplier(client, company_id=company["id"], legal_name="JHONNY ALEXANDER VALLADARES SUAZO")

    advance_asset = create_account(client, company_id=company["id"], code="1610", name="Anticipos a contratistas", account_type="ASSET")
    cost_5101 = create_account(client, company_id=company["id"], code="5101", name="Costos directos de construcción", account_type="EXPENSE")
    admin_6101 = create_account(client, company_id=company["id"], code="6101", name="Gastos administrativos generales", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2101", name="Cuentas por pagar — Proveedores", account_type="LIABILITY")
    contrib = create_account(client, company_id=company["id"], code="3101", name="Aportes", account_type="EQUITY")
    bank_gl = create_account(client, company_id=company["id"], code="1102", name="Banco principal HNL", account_type="ASSET")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    client.post("/api/treasury/remittances", json={
        "companyId": company["id"], "treasuryAccountId": bank["id"], "counterAccountId": contrib["id"],
        "sender": "Fondeo", "currencyCode": "HNL", "originalAmount": "2000000.00", "remittanceDate": "2026-01-01",
    })

    company_row = db_session.get(Company, company["id"])
    company_row.supplier_advance_account_id = advance_asset["id"]
    db_session.commit()

    project = client.post("/api/projects", json={
        "companyId": company["id"], "name": "Construcción de Residencia Principal", "code": "3201", "currencyCode": "HNL",
    }).json()
    client.post(f"/api/projects/{project['id']}/budgets/baseline", json={
        "currencyCode": "HNL", "lines": [{"authorizedAmount": "2000000.00"}],
    })
    contract = client.post("/api/procurement/suppliers/contracts", json={
        "companyId": company["id"], "supplierId": supplier["id"], "projectId": project["id"],
        "contractNumber": "10101960", "value": "1500000.00", "currencyCode": "HNL",
        "startDate": "2026-08-01", "advanceAmount": "50000.00", "advanceDueDate": "2026-08-22", "retentionPercentage": "0",
    }).json()
    schedule = client.post("/api/contract-payments/schedules", json={
        "supplierContractId": contract["id"], "scheduleType": "MONTHLY",
        "regularMonths": 7, "dueDay": 1, "firstPeriod": "2026-09-01",
    }).json()

    # GeneralExpense — la salida de caja REAL (Debit 5101 / Credit Tesorería).
    gge = client.post("/api/treasury/general-expenses", json={
        "companyId": company["id"], "treasuryAccountId": bank["id"], "expenseAccountId": cost_5101["id"],
        "scope": "PROJECT", "projectId": project["id"], "category": "mano_de_obra",
        "amount": "50000.00", "currencyCode": "HNL", "expenseDate": "2026-08-22",
        "description": "Anticipo contractual de mano de obra correspondiente al contrato 10101960.",
        "acknowledgeContractualConflict": True,
        "contractualConflictReason": "Registro legacy previo al guard contractual",
    })
    assert gge.status_code == 201, gge.text
    gge_body = gge.json()

    # SupplierInvoice DUPLICADA por el mismo anticipo (Debit 6101 / Credit CxP), aprobada.
    invoice = client.post("/api/ap/supplier-invoices", json={
        "companyId": company["id"], "supplierId": supplier["id"], "invoiceNumber": "2020485218",
        "scope": "PROJECT", "projectId": project["id"], "expenseAccountId": admin_6101["id"],
        "payableAccountId": payable["id"], "currencyCode": "HNL", "amount": "50000.00",
        "invoiceDate": "2026-09-02", "dueDate": "2026-09-02", "supplierContractId": contract["id"],
    }).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")

    return company, project, contract, schedule, bank, gge_body, invoice, cost_5101, admin_6101, advance_asset


def test_reconcile_duplicated_advance_end_to_end(client, db_session):
    company, project, contract, schedule, bank, gge, invoice, cost_5101, admin_6101, advance_asset = _setup(client, db_session)

    # --- estado incorrecto ANTES ---
    assert _bank_balance(client, company["id"], bank["id"]) == Decimal("1950000.00")  # −50k una vez
    inv_before = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert inv_before["status"] == "APPROVED"

    result = ars.reconcile_duplicated_advance(
        db_session,
        general_expense_id=gge["id"],
        supplier_invoice_id=invoice["id"],
        contract_number="10101960",
        reason="Duplicación de anticipo detectada y autorizada — ORDEN MAESTRA DE CIERRE §23",
        correlation_id="cierre-l50k-test",
        commit=True,
    )
    assert result["amount"] == "50000.00"

    db_session.expire_all()

    # 1) La caja NO se movió otra vez.
    assert _bank_balance(client, company["id"], bank["id"]) == Decimal("1950000.00")

    # 2) Factura duplicada revertida, sin obligación abierta.
    inv_after = client.get(f"/api/ap/supplier-invoices/{invoice['id']}").json()
    assert inv_after["status"] == "CANCELLED"
    assert result["after"]["invoiceExpenseAccountBalance"] == "0.00"   # 6101 neteado
    assert result["after"]["generalExpenseExpenseAccountBalance"] == "0.00"  # 5101 reclasificado

    # 3) El anticipo quedó en la cuenta ASSET.
    asset_bal = ars._account_gl_total(db_session, account_id=advance_asset["id"], project_id=project["id"])
    assert asset_bal == Decimal("50000.00")

    # 4) Contrato: anticipo pagado, saldo 1,450,000.
    summary = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(summary["advancePaid"]) == Decimal("50000.00")
    assert Decimal(summary["advanceRemaining"]) == Decimal("0.00")
    assert Decimal(summary["paidAccumulated"]) == Decimal("50000.00")
    assert Decimal(summary["contractBalance"]) == Decimal("1450000.00")

    adv = next(
        s for s in cps.installment_summaries(db_session, schedule_id=schedule["id"])
        if s.installment_kind == "ADVANCE"
    )
    assert adv.paid == Decimal("50000.00")
    assert adv.status == "PAID"

    # 5) Subledger ↔ GL cuadra.
    recon = client.get(f"/api/accounting/reconciliation/subledger-gl?companyId={company['id']}").json()
    assert recon["allReconciled"], recon

    # 6) Presupuesto: el anticipo es advance, no costo devengado.
    budget = client.get(f"/api/projects/{project['id']}/budgets/summary").json()
    assert Decimal(budget["accrued"]) == Decimal("0.00")
    assert Decimal(budget["advances"]) == Decimal("50000.00")


def test_inspect_classifies_reconciled_advance_as_clean(client, db_session):
    company, project, contract, schedule, bank, gge, invoice, *_ = _setup(client, db_session)
    from decimal import Decimal as D

    from scripts.financial_event_inspect import Filters, inspect

    before = inspect(db_session, Filters(company=company["id"], amount=D("50000")))
    assert before.classification["category"] in (
        "ADVANCE_MISCLASSIFIED_AS_EXPENSE",
        "DUPLICATED_BUSINESS_EVENT",
    )

    ars.reconcile_duplicated_advance(
        db_session,
        general_expense_id=gge["id"],
        supplier_invoice_id=invoice["id"],
        contract_number="10101960",
        reason="Duplicación de anticipo autorizada — ORDEN MAESTRA DE CIERRE §23",
        correlation_id="cierre-l50k-clean",
        commit=True,
    )
    db_session.expire_all()

    after = inspect(db_session, Filters(company=company["id"], amount=D("50000")))
    assert after.classification["category"] == "CLEAN"
    assert not any("POSIBLE DOBLE CONTEO" in n for n in after.notes)
    assert any("ya reconciliado" in n for n in after.notes)


def test_finalize_reversed_invoice_closes_stuck_approved(client, db_session):
    company, project, contract, schedule, bank, gge, invoice, *_ = _setup(client, db_session)
    from app.models.accounting import AccountingDocument
    from app.models.ap import SupplierInvoice
    from app.services import posting_service
    from scripts import financial_reconciliation as fr

    inv = db_session.get(SupplierInvoice, invoice["id"])
    posting_service.reverse_document(
        db_session, document_id=inv.accrual_document_id, reason="reverso sin hook " * 3, commit=False
    )
    # estado "atascado": el accrual quedó REVERSED pero la factura volvió a APPROVED
    inv.status = "APPROVED"
    db_session.commit()
    assert db_session.get(AccountingDocument, inv.accrual_document_id).status == "REVERSED"

    rc = fr.main(["--mode", "finalize-reversed-invoice-preview", "--invoice-number", "2020485218"])
    assert rc == 0
    db_session.expire_all()
    assert db_session.get(SupplierInvoice, invoice["id"]).status == "APPROVED"  # preview no persiste

    rc = fr.main([
        "--mode", "finalize-reversed-invoice-apply", "--invoice-number", "2020485218",
        "--confirm", "APPLY", "--reason", "cierre de reverso pendiente ORDEN MAESTRA DE CIERRE",
    ])
    assert rc == 0
    db_session.expire_all()
    assert db_session.get(SupplierInvoice, invoice["id"]).status == "CANCELLED"


def test_finalize_reversed_invoice_blocks_when_accrual_still_posted(client, db_session):
    company, *_rest, invoice, _c, _a, _adv = _setup(client, db_session)
    from scripts import financial_reconciliation as fr

    rc = fr.main(["--mode", "finalize-reversed-invoice-preview", "--invoice-number", "2020485218"])
    assert rc == 3  # accrual sigue POSTED


def test_reconcile_rejects_amount_mismatch(client, db_session):
    company, project, contract, schedule, bank, gge, invoice, *_ = _setup(client, db_session)
    import pytest
    from app.domain.errors import InvalidFinancialReferenceError

    with pytest.raises(InvalidFinancialReferenceError):
        ars.reconcile_duplicated_advance(
            db_session,
            general_expense_id=gge["id"],
            supplier_invoice_id=invoice["id"],
            contract_number="NOPE-9999",
            reason="x" * 20,
            correlation_id="t",
        )
