"""contract payment control: schedules, installments, allocations + invoice-contract link

Revision ID: 2640b82e65b8
Revises: 7163bfe08fdb
Create Date: 2026-09-01

Orden maestra final — Project Contract Payment Control (§1-§16, §46-§53).
Subledger contractual: schedule -> installment -> allocation -> supplier_payment.
`supplier_invoices.supplier_contract_id` enlaza la obligación con su contrato.
No destructiva; sin backfill (los contratos existentes obtienen su plan cuando
alguien lo cree).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2640b82e65b8"
down_revision: Union[str, None] = "7163bfe08fdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "supplier_invoices",
        sa.Column(
            "supplier_contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("supplier_contracts.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_supplier_invoices_supplier_contract_id",
        "supplier_invoices",
        ["supplier_contract_id"],
    )

    op.create_table(
        "contract_payment_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supplier_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_contracts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("schedule_type", sa.String(16), nullable=False, server_default="MONTHLY"),
        sa.Column("start_period", sa.Date(), nullable=False),
        sa.Column("end_period", sa.Date(), nullable=True),
        sa.Column("total_scheduled", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("supplier_contract_id", name="uq_contract_payment_schedule_contract"),
        sa.CheckConstraint("total_scheduled >= 0", name="ck_contract_payment_schedule_total"),
    )

    op.create_table(
        "contract_payment_installments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contract_payment_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("scheduled_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("retention_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("net_due", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="UPCOMING"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("schedule_id", "sequence", name="uq_contract_installment_sequence"),
        sa.UniqueConstraint("schedule_id", "period_year", "period_month", name="uq_contract_installment_period"),
        sa.CheckConstraint("scheduled_amount > 0", name="ck_contract_installment_amount"),
        sa.CheckConstraint("retention_amount >= 0", name="ck_contract_installment_retention"),
        sa.CheckConstraint("sequence >= 1", name="ck_contract_installment_sequence"),
        sa.CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_contract_installment_month"),
    )
    op.create_index("ix_contract_payment_installments_schedule_id", "contract_payment_installments", ["schedule_id"])

    op.create_table(
        "contract_payment_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("installment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contract_payment_installments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_applied", sa.Numeric(18, 2), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("override_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("supplier_payment_id", "installment_id", name="uq_contract_allocation_payment_installment"),
        sa.CheckConstraint("amount_applied > 0", name="ck_contract_allocation_amount"),
    )
    op.create_index("ix_contract_payment_allocations_supplier_payment_id", "contract_payment_allocations", ["supplier_payment_id"])
    op.create_index("ix_contract_payment_allocations_installment_id", "contract_payment_allocations", ["installment_id"])


def downgrade() -> None:
    op.drop_table("contract_payment_allocations")
    op.drop_index("ix_contract_payment_installments_schedule_id", table_name="contract_payment_installments")
    op.drop_table("contract_payment_installments")
    op.drop_table("contract_payment_schedules")
    op.drop_index("ix_supplier_invoices_supplier_contract_id", table_name="supplier_invoices")
    op.drop_column("supplier_invoices", "supplier_contract_id")
