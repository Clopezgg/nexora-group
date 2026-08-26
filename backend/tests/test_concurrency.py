"""Master order §10 (Concurrency/Idempotency): real races, not sequential
tests where duplicate money/inventory/documents could theoretically slip
through. Every test here uses genuinely independent threads, each with
its OWN SQLAlchemy `Session` (never the shared `db_session` fixture,
which is not thread-safe and would not reproduce a real multi-request
race) against the SAME live PostgreSQL test database the rest of the
suite uses. `client`/`db_session` are used only for single-threaded
setup before the race starts."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.core.database import SessionLocal
from app.domain.errors import (
    IdempotencyConflictError,
    InsufficientStockError,
    InvalidInvoiceStateError,
    InvalidProcurementStateError,
    OverpaymentError,
)
from app.services import (
    ap_service,
    idempotency_service,
    inventory_service,
    numbering_service,
    procurement_service,
    treasury_service,
)
from tests.helpers import (
    create_account,
    create_company,
    create_supplier,
    create_treasury_account,
    login_admin,
)


def test_concurrent_numbering_never_produces_a_duplicate_number_first_call_ever(client, db_session):
    """The create-race: the sequence row doesn't exist yet, so N
    concurrent callers all see `sequence is None` before any of them
    commits -- exercises both the SELECT...FOR UPDATE steady-state path
    AND the INSERT-time unique constraint (uq_number_sequences_scope) as
    the real last line of defense."""
    login_admin(client)
    company = create_company(client)
    company_id = uuid.UUID(company["id"])
    db_session.commit()

    def _issue_one() -> str:
        db = SessionLocal()
        try:
            number = numbering_service.next_document_number(
                db, company_id=company_id, document_type_code="PO"
            )
            db.commit()
            return number
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_issue_one) for _ in range(10)]
        results = []
        errors = []
        for f in futures:
            try:
                results.append(f.result())
            except Exception as exc:  # noqa: BLE001 -- we want to see exactly what a real race raises
                errors.append(exc)

    # The invariant that actually matters: no two SUCCESSFUL callers ever
    # got the same number. A caller failing outright (and the real
    # caller retrying, same as any transient DB conflict) is acceptable;
    # two callers walking away with the same PO number is not.
    assert len(results) == len(set(results)), f"duplicate document numbers issued: {results}"
    assert len(results) + len(errors) == 10


def test_concurrent_numbering_never_produces_a_duplicate_number_steady_state(client, db_session):
    """Once the sequence row already exists, SELECT...FOR UPDATE should
    serialize every concurrent caller cleanly -- zero errors expected,
    not just zero duplicates."""
    login_admin(client)
    company = create_company(client)
    company_id = uuid.UUID(company["id"])
    # Force the sequence row to exist before the real race starts.
    seed_db = SessionLocal()
    numbering_service.next_document_number(seed_db, company_id=company_id, document_type_code="PO")
    seed_db.commit()
    seed_db.close()
    db_session.commit()

    def _issue_one() -> str:
        db = SessionLocal()
        try:
            number = numbering_service.next_document_number(
                db, company_id=company_id, document_type_code="PO"
            )
            db.commit()
            return number
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: _issue_one(), range(20)))

    assert len(results) == len(set(results)) == 20


def test_concurrent_idempotency_replay_executes_the_real_operation_exactly_once(client, db_session):
    """Two concurrent requests with the SAME Idempotency-Key must result
    in the real side effect happening exactly once -- one caller does the
    real work, the other gets the replayed result, never both doing it
    and never both getting a blank/failed response."""
    login_admin(client)
    company = create_company(client)
    company_id = uuid.UUID(company["id"])
    db_session.commit()

    key = str(uuid.uuid4())
    payload = {"amount": "100.00"}
    execution_count = {"n": 0}

    def _attempt() -> str:
        db = SessionLocal()
        try:
            outcome = idempotency_service.begin(
                db, key=key, command="test.concurrency.op", payload=payload
            )
            if outcome.is_replay:
                return "replay"
            # Simulate the real side effect a real command would perform
            # while holding the idempotency row's lock.
            execution_count["n"] += 1
            idempotency_service.complete(db, record=outcome.record, result={"ok": True})
            db.commit()
            return "executed"
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_attempt) for _ in range(5)]
        outcomes = []
        errors = []
        for f in futures:
            try:
                outcomes.append(f.result())
            except IdempotencyConflictError as exc:
                errors.append(exc)

    assert errors == [], f"no concurrent caller should error at all, got: {errors}"
    assert execution_count["n"] == 1, f"real side effect ran {execution_count['n']} times, expected exactly 1"
    assert outcomes.count("executed") == 1
    assert outcomes.count("replay") == 4


def test_concurrent_remittances_never_lose_an_update_to_the_treasury_balance(client, db_session):
    """Two concurrent CENTRAL remittances into the SAME treasury account
    must both land -- a lost update here would mean real money vanishing
    from the reported balance while the GL still shows it posted."""
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    contributions_gl = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    company_id = uuid.UUID(company["id"])
    treasury_account_id = uuid.UUID(bank["id"])
    counter_account_id = uuid.UUID(contributions_gl["id"])
    db_session.commit()

    def _remit() -> None:
        db = SessionLocal()
        try:
            treasury_service.register_remittance(
                db, company_id=company_id, treasury_account_id=treasury_account_id,
                counter_account_id=counter_account_id, sender="Socio", provider=None, channel=None,
                currency_code="HNL", original_amount=Decimal("100.00"), fx_rate=Decimal("1"),
                reference=None, remittance_date=date(2026, 1, 1), notes=None,
            )
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(lambda _: _remit(), range(10)))

    balance = treasury_service.account_balance(db_session, gl_account_id=uuid.UUID(bank_gl["id"]))
    assert balance == Decimal("1000.00"), f"expected 10 x L100.00 = L1000.00, got {balance} (lost update)"


def test_concurrent_full_payments_on_the_same_invoice_never_double_pay(client, db_session):
    """N concurrent attempts to pay the SAME invoice for its FULL amount
    must result in exactly one successful payment -- a lost update on
    `SupplierInvoice.amount_paid` here would mean real money leaving
    Treasury twice for one real debt.

    `pay_supplier_invoice` takes `SELECT ... FOR UPDATE` on the invoice
    row itself, so callers serialize: the winner pays and flips
    `status` to PAID before releasing the lock, so every loser hits the
    status guard (`status not in (APPROVED, SCHEDULED, PARTIALLY_PAID)`)
    -- InvalidInvoiceStateError -- before it would ever reach the
    overpayment guard. Both exceptions represent a correctly-rejected
    duplicate payment; which one fires is just a matter of which guard
    the loser's now-stale in-memory view of `status` trips first."""
    login_admin(client)
    company = create_company(client)
    bank_gl = create_account(client, company_id=company["id"], code="1100", name="Bancos", account_type="ASSET")
    expense_gl = create_account(client, company_id=company["id"], code="5200", name="Gastos", account_type="EXPENSE")
    payable_gl = create_account(client, company_id=company["id"], code="2100", name="CxP", account_type="LIABILITY")
    contributions_gl = create_account(
        client, company_id=company["id"], code="3100", name="Aportes", account_type="EQUITY"
    )
    bank = create_treasury_account(client, company_id=company["id"], gl_account_id=bank_gl["id"])
    supplier = create_supplier(client, company_id=company["id"])
    client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"], "treasuryAccountId": bank["id"], "counterAccountId": contributions_gl["id"],
            "sender": "Fondeo", "currencyCode": "HNL", "originalAmount": "10000.00", "remittanceDate": "2026-01-01",
        },
    )
    invoice = client.post(
        "/api/ap/supplier-invoices",
        json={
            "companyId": company["id"], "supplierId": supplier["id"], "invoiceNumber": "FAC-RACE-001",
            "scope": "GENERAL", "expenseAccountId": expense_gl["id"], "payableAccountId": payable_gl["id"],
            "currencyCode": "HNL", "amount": "1000.00", "invoiceDate": "2026-01-05", "dueDate": "2026-02-05",
        },
    ).json()
    client.post(f"/api/ap/supplier-invoices/{invoice['id']}/approve")
    db_session.commit()

    invoice_id = uuid.UUID(invoice["id"])
    treasury_account_id = uuid.UUID(bank["id"])

    def _pay() -> str:
        db = SessionLocal()
        try:
            ap_service.pay_supplier_invoice(
                db, invoice_id=invoice_id, treasury_account_id=treasury_account_id,
                amount=Decimal("1000.00"), payment_date=date(2026, 1, 10),
            )
            return "paid"
        except (OverpaymentError, InvalidInvoiceStateError):
            return "rejected"
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        outcomes = list(pool.map(lambda _: _pay(), range(5)))

    assert outcomes.count("paid") == 1, f"expected exactly 1 successful payment, got: {outcomes}"
    assert outcomes.count("rejected") == 4

    db_session.expire_all()
    updated_invoice = db_session.execute(
        text("SELECT amount_paid, status FROM supplier_invoices WHERE id = :id"),
        {"id": str(invoice_id)},
    ).one()
    assert Decimal(updated_invoice[0]) == Decimal("1000.00")
    assert updated_invoice[1] == "PAID"


def test_concurrent_goods_receipts_never_over_receive_beyond_ordered_quantity(client, db_session):
    """N concurrent goods receipts against the SAME PO line, together
    requesting more than what was ordered, must never let the sum of
    `quantity_received` exceed `quantity` -- a lost update here means
    inventory and AP/3-way-match obligations get recorded for stock that
    was never actually ordered. Real bug found here: `record_goods_receipt`
    read `PurchaseOrderLine.quantity_received` via a plain `db.get()` (no
    lock), so N concurrent receipts could all read the same stale value
    and all pass the remaining-quantity guard. Fixed with
    `procurement_repository.get_purchase_order_line_for_update`."""
    login_admin(client)
    company = create_company(client)
    company_id = uuid.UUID(company["id"])
    admin_id = uuid.UUID(client.get("/api/auth/me").json()["id"])
    supplier = create_supplier(client, company_id=company["id"])
    item = client.post(
        "/api/inventory/items",
        json={
            "companyId": company["id"], "sku": "RACE-001", "name": "Varilla 3/8",
            "itemType": "MATERIAL", "uom": "UND",
        },
    ).json()
    warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-RACE-1", "name": "Almacén Race 1"},
    ).json()
    po = client.post(
        "/api/procurement/purchase-orders",
        json={
            "companyId": company["id"], "supplierId": supplier["id"], "currencyCode": "HNL",
            "lines": [
                {"itemId": item["id"], "description": "Varilla 3/8", "quantity": "100.0000", "unitPrice": "5.0000"}
            ],
        },
    ).json()
    client.post(f"/api/procurement/purchase-orders/{po['id']}/approve")
    client.post(f"/api/procurement/purchase-orders/{po['id']}/send")
    purchase_order_id = uuid.UUID(po["id"])
    po_line_id = uuid.UUID(po["lines"][0]["id"])
    warehouse_id = uuid.UUID(warehouse["id"])
    db_session.commit()

    def _receive() -> str:
        db = SessionLocal()
        try:
            procurement_service.record_goods_receipt(
                db,
                company_id=company_id,
                purchase_order_id=purchase_order_id,
                warehouse_id=warehouse_id,
                received_by_id=admin_id,
                received_at=date(2026, 1, 10),
                quality_notes=None,
                lines=[{"purchase_order_line_id": po_line_id, "quantity_received": Decimal("30.0000")}],
            )
            return "received"
        except InvalidProcurementStateError:
            return "rejected"
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        outcomes = list(pool.map(lambda _: _receive(), range(5)))

    # 100 ordered / 30 per attempt -> at most 3 can ever fit (90 <= 100);
    # the 4th would need 120, which no single serialized attempt allows.
    assert outcomes.count("received") == 3, f"expected exactly 3 successful receipts, got: {outcomes}"
    assert outcomes.count("rejected") == 2

    db_session.expire_all()
    total_received = db_session.execute(
        text("SELECT quantity_received FROM purchase_order_lines WHERE id = :id"),
        {"id": str(po_line_id)},
    ).scalar_one()
    assert Decimal(total_received) == Decimal("90.0000"), (
        f"over-received beyond the 100.0000 ordered: {total_received}"
    )


def test_concurrent_stock_issues_never_over_issue_beyond_on_hand_quantity(client, db_session):
    """N concurrent stock issues from the SAME item/warehouse, together
    requesting more than what's on hand, must never let combined issues
    exceed real stock. Real bug found here: `inventory_service._issue`/
    `_receive_stock_entry` derived the current position from the LAST
    `StockLedgerEntry` via a plain (unlocked) query -- the ledger is
    append-only, so there is no single mutable row a normal
    `SELECT...FOR UPDATE` could lock that would actually block a
    concurrent INSERT from a different transaction (classic phantom-row
    problem). Fixed with a `pg_advisory_xact_lock` keyed by
    (company, item, warehouse) in `_lock_stock_position`."""
    login_admin(client)
    company = create_company(client)
    company_id = uuid.UUID(company["id"])
    item = client.post(
        "/api/inventory/items",
        json={
            "companyId": company["id"], "sku": "RACE-002", "name": "Cemento",
            "itemType": "MATERIAL", "uom": "SACO",
        },
    ).json()
    warehouse = client.post(
        "/api/inventory/warehouses",
        json={"companyId": company["id"], "code": "ALM-RACE-2", "name": "Almacén Race 2"},
    ).json()
    project = client.post(
        "/api/projects",
        json={"companyId": company["id"], "name": "Proyecto Race", "code": "PRJ-RACE", "currencyCode": "HNL"},
    ).json()
    item_id = uuid.UUID(item["id"])
    warehouse_id = uuid.UUID(warehouse["id"])
    project_id = uuid.UUID(project["id"])
    db_session.commit()

    seed_db = SessionLocal()
    inventory_service.receive_stock(
        seed_db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("10.0000"),
    )
    seed_db.commit()
    seed_db.close()
    db_session.commit()

    def _issue() -> str:
        db = SessionLocal()
        try:
            inventory_service.issue_to_project(
                db,
                company_id=company_id,
                item_id=item_id,
                warehouse_id=warehouse_id,
                project_id=project_id,
                quantity=Decimal("30.0000"),
            )
            return "issued"
        except InsufficientStockError:
            return "rejected"
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        outcomes = list(pool.map(lambda _: _issue(), range(5)))

    # 100 on hand / 30 per attempt -> at most 3 fit (90 <= 100).
    assert outcomes.count("issued") == 3, f"expected exactly 3 successful issues, got: {outcomes}"
    assert outcomes.count("rejected") == 2

    db_session.expire_all()
    final_position = db_session.execute(
        text(
            "SELECT resulting_qty_on_hand FROM stock_ledger_entries "
            "WHERE item_id = :item_id AND warehouse_id = :warehouse_id "
            "ORDER BY entry_seq DESC LIMIT 1"
        ),
        {"item_id": str(item_id), "warehouse_id": str(warehouse_id)},
    ).scalar_one()
    assert Decimal(final_position) == Decimal("10.0000"), (
        f"expected 100 - (3 x 30) = 10 on hand, got {final_position} (lost update / over-issue)"
    )
