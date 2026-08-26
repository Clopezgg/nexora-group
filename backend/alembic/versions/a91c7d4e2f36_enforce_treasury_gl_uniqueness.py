"""enforce treasury gl uniqueness

Revision ID: a91c7d4e2f36
Revises: 58ce35982711
Create Date: 2026-08-24

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a91c7d4e2f36"
down_revision: Union[str, None] = "58ce35982711"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_treasury_accounts_gl_account",
        "treasury_accounts",
        ["gl_account_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_treasury_accounts_gl_account",
        "treasury_accounts",
        type_="unique",
    )
