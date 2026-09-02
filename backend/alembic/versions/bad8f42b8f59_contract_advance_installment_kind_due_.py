"""contract advance + installment kind + due day + advance account

Revision ID: bad8f42b8f59
Revises: 5fd1404e9a87
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "bad8f42b8f59"
down_revision: Union[str, None] = "5fd1404e9a87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- supplier_contracts: anticipo monetario canónico -------------------
    op.add_column("supplier_contracts", sa.Column("advance_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("supplier_contracts", sa.Column("advance_due_date", sa.Date(), nullable=True))
    op.create_check_constraint(
        "ck_supplier_contracts_advance_pct", "supplier_contracts",
        "advance_percentage >= 0 AND advance_percentage <= 100",
    )
    op.create_check_constraint(
        "ck_supplier_contracts_retention_pct", "supplier_contracts",
        "retention_percentage >= 0 AND retention_percentage <= 100",
    )
    op.create_check_constraint(
        "ck_supplier_contracts_advance_amount", "supplier_contracts",
        "advance_amount IS NULL OR (advance_amount >= 0 AND advance_amount <= value)",
    )

    # --- contract_payment_schedules: due_day ------------------------------
    op.add_column("contract_payment_schedules", sa.Column("due_day", sa.Integer(), nullable=True))

    # --- contract_payment_installments: installment_kind -----------------
    op.add_column(
        "contract_payment_installments",
        sa.Column("installment_kind", sa.String(length=20), nullable=False, server_default="REGULAR"),
    )
    op.create_check_constraint(
        "ck_contract_installment_kind", "contract_payment_installments",
        "installment_kind IN ('ADVANCE', 'REGULAR', 'RETENTION_RELEASE')",
    )
    op.drop_constraint("uq_contract_installment_period", "contract_payment_installments", type_="unique")
    op.create_unique_constraint(
        "uq_contract_installment_period", "contract_payment_installments",
        ["schedule_id", "period_year", "period_month", "installment_kind"],
    )

    # --- companies: cuenta de anticipos --------------------------------
    # Sin FK a nivel DB para evitar el ciclo companies<->accounts (se valida en
    # el servicio, mismo criterio que logo_evidence_id).
    op.add_column(
        "companies",
        sa.Column(
            "supplier_advance_account_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "supplier_advance_account_id")
    op.drop_constraint("uq_contract_installment_period", "contract_payment_installments", type_="unique")
    op.create_unique_constraint(
        "uq_contract_installment_period", "contract_payment_installments",
        ["schedule_id", "period_year", "period_month"],
    )
    op.drop_constraint("ck_contract_installment_kind", "contract_payment_installments", type_="check")
    op.drop_column("contract_payment_installments", "installment_kind")
    op.drop_column("contract_payment_schedules", "due_day")
    op.drop_constraint("ck_supplier_contracts_advance_amount", "supplier_contracts", type_="check")
    op.drop_constraint("ck_supplier_contracts_retention_pct", "supplier_contracts", type_="check")
    op.drop_constraint("ck_supplier_contracts_advance_pct", "supplier_contracts", type_="check")
    op.drop_column("supplier_contracts", "advance_due_date")
    op.drop_column("supplier_contracts", "advance_amount")
