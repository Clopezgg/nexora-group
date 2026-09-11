from decimal import Decimal

from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def _pay_installment(client, *, context: dict, installment: dict, invoice_number: str) -> dict:
    invoice_response = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": context["company"]["id"],
            "supplierId": context["supplier"]["id"],
            "invoiceNumber": invoice_number,
            "scope": "GENERAL",
            "expenseAccountId": context["expense"]["id"],
            "payableAccountId": context["payable"]["id"],
            "currencyCode": "HNL",
            "amount": installment["netDue"],
            "invoiceDate": installment["dueDate"],
            "dueDate": installment["dueDate"],
            "supplierContractId": context["contract"]["id"],
            "contractInstallmentId": installment["installmentId"],
        },
    )
    assert invoice_response.status_code == 201, invoice_response.text
    invoice = invoice_response.json()
    approved = client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    assert approved.status_code == 200, approved.text
    payment_response = client.post(
        f"/api/ap/supplier-invoices/{invoice['id']}/payments",
        json={
            "treasuryAccountId": context["bank"]["id"],
            "amount": installment["netDue"],
            "paymentDate": installment["dueDate"],
            "paymentMethod": "OTHER",
            "contractAllocations": [
                {
                    "installmentId": installment["installmentId"],
                    "amountApplied": installment["netDue"],
                }
            ],
        },
    )
    assert payment_response.status_code == 201, payment_response.text
    return payment_response.json()


def test_retention_withheld_release_payment_and_reversal_lifecycle(client):
    login_admin(client)
    company = create_company(client, name="Retención Lifecycle")
    supplier = create_supplier(client, company_id=company["id"])
    expense = create_account(client, company_id=company["id"], code="5200", name="Obra", account_type="EXPENSE")
    payable = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Banco", account_type="ASSET")
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    contract_response = client.post(
        "/api/procurement/suppliers/contracts",
        json={
            "companyId": company["id"],
            "supplierId": supplier["id"],
            "contractNumber": "RET-LIFECYCLE",
            "value": "100000.00",
            "currencyCode": "HNL",
            "startDate": "2026-01-01",
            "retentionPercentage": "5",
            "paymentTermsType": "MONTHLY",
        },
    )
    assert contract_response.status_code == 201, contract_response.text
    contract = contract_response.json()
    schedule_response = client.post(
        "/api/contract-payments/schedules",
        json={
            "supplierContractId": contract["id"],
            "scheduleType": "MONTHLY",
            "regularMonths": 2,
            "dueDay": 1,
            "firstPeriod": "2026-01-01",
        },
    )
    assert schedule_response.status_code == 201, schedule_response.text
    schedule = schedule_response.json()
    context = {
        "company": company,
        "supplier": supplier,
        "expense": expense,
        "payable": payable,
        "bank": bank,
        "contract": contract,
    }

    initial = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(initial["retentionWithheld"]) == Decimal("0.00")
    assert Decimal(initial["retentionOutstanding"]) == Decimal("0.00")

    for index, installment in enumerate(schedule["installments"], start=1):
        _pay_installment(client, context=context, installment=installment, invoice_number=f"RET-NET-{index}")

    withheld = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(withheld["paidAccumulated"]) == Decimal("95000.00")
    assert Decimal(withheld["contractBalance"]) == Decimal("5000.00")
    assert Decimal(withheld["retentionWithheld"]) == Decimal("5000.00")
    assert Decimal(withheld["retentionReleased"]) == Decimal("0.00")
    assert Decimal(withheld["retentionPaid"]) == Decimal("0.00")
    assert Decimal(withheld["retentionOutstanding"]) == Decimal("5000.00")

    release_response = client.post(
        f"/api/contract-payments/schedules/{schedule['id']}/retention-releases",
        json={
            "amount": "5000.00",
            "dueDate": "2026-03-01",
            "reason": "Acta de recepción final autoriza la liberación",
        },
    )
    assert release_response.status_code == 201, release_response.text
    release_schedule = release_response.json()
    release = next(i for i in release_schedule["installments"] if i["installmentKind"] == "RETENTION_RELEASE")
    assert release["netDue"] == "5000.00"
    assert release["payableNow"] is True

    authorized = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(authorized["retentionReleased"]) == Decimal("5000.00")
    assert Decimal(authorized["retentionAvailableToRelease"]) == Decimal("0.00")
    release_payment = _pay_installment(
        client,
        context=context,
        installment=release,
        invoice_number="RET-RELEASE",
    )

    completed = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(completed["paidAccumulated"]) == Decimal("100000.00")
    assert Decimal(completed["contractBalance"]) == Decimal("0.00")
    assert Decimal(completed["retentionPaid"]) == Decimal("5000.00")
    assert Decimal(completed["retentionOutstanding"]) == Decimal("0.00")
    assert client.get(f"/api/contract-payments/by-contract/{contract['id']}").json()["status"] == "COMPLETED"

    reversed_response = client.post(
        f"/api/ap/supplier-payments/{release_payment['id']}/reverse",
        json={"reason": "Pago de liberación anulado por rechazo bancario"},
    )
    assert reversed_response.status_code == 200, reversed_response.text
    reversed_summary = client.get(f"/api/contract-payments/schedules/{schedule['id']}/summary").json()
    assert Decimal(reversed_summary["contractBalance"]) == Decimal("5000.00")
    assert Decimal(reversed_summary["retentionPaid"]) == Decimal("0.00")
    assert Decimal(reversed_summary["retentionOutstanding"]) == Decimal("5000.00")
    assert client.get(f"/api/contract-payments/by-contract/{contract['id']}").json()["status"] == "ACTIVE"
