"""contract payment allocation: allow a GeneralExpense as the cash source

Revision ID: d4b9f1c07e33
Revises: c1a7e4f9b210
Create Date: 2026-09-02

ORDEN MAESTRA DE CIERRE §7 — un anticipo contractual cuya salida de caja se
registró como GeneralExpense (y no como SupplierPayment) debe poder asignarse
a la cuota ADVANCE del contrato. Se relaja `supplier_payment_id` a nullable y
se añade `general_expense_id`; exactamente una de las dos fuentes está puesta.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4b9f1c07e33"
down_revision: Union[str, None] = "c1a7e4f9b210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "contract_payment_allocations",
        "supplier_payment_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.add_column(
        "contract_payment_allocations",
        sa.Column("general_expense_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_contract_allocation_general_expense",
        "contract_payment_allocations",
        "general_expenses",
        ["general_expense_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_contract_payment_allocations_general_expense_id",
        "contract_payment_allocations",
        ["general_expense_id"],
    )
    op.create_check_constraint(
        "ck_contract_allocation_one_source",
        "contract_payment_allocations",
        "(supplier_payment_id IS NOT NULL) <> (general_expense_id IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_contract_allocation_general_expense_installment",
        "contract_payment_allocations",
        ["general_expense_id", "installment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_contract_allocation_general_expense_installment",
        "contract_payment_allocations",
        type_="unique",
    )
    op.drop_constraint(
        "ck_contract_allocation_one_source", "contract_payment_allocations", type_="check"
    )
    op.drop_index(
        "ix_contract_payment_allocations_general_expense_id",
        table_name="contract_payment_allocations",
    )
    op.drop_constraint(
        "fk_contract_allocation_general_expense",
        "contract_payment_allocations",
        type_="foreignkey",
    )
    op.drop_column("contract_payment_allocations", "general_expense_id")
    op.execute(
        "DELETE FROM contract_payment_allocations WHERE supplier_payment_id IS NULL"
    )
    op.alter_column(
        "contract_payment_allocations",
        "supplier_payment_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
