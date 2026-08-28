"""add change order contract impact

Revision ID: 8f5d2c7e1a44
Revises: a1b2c3d4e5f6
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8f5d2c7e1a44"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "change_orders",
        sa.Column(
            "contract_change_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column("change_orders", "contract_change_amount", server_default=None)


def downgrade() -> None:
    op.drop_column("change_orders", "contract_change_amount")
