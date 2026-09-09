"""add fiscal core database constraints

Revision ID: c2d4e6f8a0b1
Revises: b83d4e9f2c11
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c2d4e6f8a0b1"
down_revision: Union[str, None] = "b83d4e9f2c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_fiscal_years_valid_date_range", "fiscal_years", "start_date <= end_date"
    )
    op.create_check_constraint(
        "ck_fiscal_periods_valid_date_range", "fiscal_periods", "start_date <= end_date"
    )
    op.create_check_constraint(
        "ck_fiscal_periods_positive_period_number", "fiscal_periods", "period_number >= 1"
    )
    op.create_check_constraint(
        "ck_fiscal_periods_valid_status", "fiscal_periods",
        "status IN ('OPEN', 'SOFT_CLOSED', 'CLOSED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_fiscal_periods_valid_status", "fiscal_periods", type_="check")
    op.drop_constraint("ck_fiscal_periods_positive_period_number", "fiscal_periods", type_="check")
    op.drop_constraint("ck_fiscal_periods_valid_date_range", "fiscal_periods", type_="check")
    op.drop_constraint("ck_fiscal_years_valid_date_range", "fiscal_years", type_="check")
