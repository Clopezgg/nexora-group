"""Standalone script (run via `python -m tests._seed_backup_restore_fixture`,
never collected by pytest) that seeds a real company + chart of accounts +
treasury account + a real posted remittance into whatever DATABASE_URL is
set in its environment, then prints the seeded IDs/amount as JSON to
stdout so the calling test can verify the same data survives a real
backup/restore cycle. Uses the actual repository/service layer -- the
same code paths every other test in this suite exercises -- never a raw
INSERT, so what gets backed up is exactly what a real user action would
have produced."""

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from decimal import Decimal  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.repositories import (  # noqa: E402
    account_repository,
    catalog_repository,
    company_repository,
    permission_repository,
    role_repository,
    user_repository,
)
from app.security.passwords import hash_password  # noqa: E402
from app.services import treasury_service  # noqa: E402

db = SessionLocal()

role_repository.ensure_base_roles(db)
permission_repository.ensure_base_permissions(db)
catalog_repository.ensure_base_currencies(db)
catalog_repository.ensure_base_document_types(db)
db.commit()

admin_role = role_repository.get_by_name(db, "Administrator")
user = user_repository.create_user(
    db, email="restored-admin@nexora.group", full_name="Restored Admin",
    password_hash=hash_password("BackupRestoreTest123!"),
)
role_repository.assign_role(db, user_id=user.id, role_id=admin_role.id)
db.commit()

company = company_repository.create_company(
    db, name="Backup Restore Co", code=None, legal_name=None,
    functional_currency_code="HNL", country=None, fiscal_id=None,
)
bank_gl = account_repository.create_account(
    db, company_id=company.id, code="1100", name="Bancos", account_type="ASSET"
)
contributions_gl = account_repository.create_account(
    db, company_id=company.id, code="3100", name="Aportes de socios", account_type="EQUITY"
)
db.commit()

bank = treasury_service.create_treasury_account(
    db, company_id=company.id, name="Banco Principal", kind="BANK",
    institution=None, account_reference=None, currency_code="HNL", gl_account_id=bank_gl.id,
)

remittance = treasury_service.register_remittance(
    db, company_id=company.id, treasury_account_id=bank.id, counter_account_id=contributions_gl.id,
    sender="Socio fundador", provider=None, channel=None, currency_code="HNL",
    original_amount=Decimal("75000.00"), fx_rate=Decimal("1"), reference=None,
    remittance_date=__import__("datetime").date(2026, 1, 15), notes=None,
)

print(json.dumps({
    "companyId": str(company.id),
    "companyName": company.name,
    "bankGlAccountId": str(bank_gl.id),
    "remittanceAmount": str(remittance.base_amount),
    "userEmail": user.email,
    "userPasswordHash": user.password_hash,
}))
