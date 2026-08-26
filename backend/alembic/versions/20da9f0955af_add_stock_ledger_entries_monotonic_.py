"""add stock ledger entries monotonic entry_seq ordering column

Revision ID: 20da9f0955af
Revises: 8496f11b1227
Create Date: 2026-08-25 23:29:22.268070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20da9f0955af'
down_revision: Union[str, None] = '8496f11b1227'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `created_at` (default `now()`) es la hora de INICIO de transacción,
    # no la hora real de escritura -- bajo contención con
    # `pg_advisory_xact_lock` (tests/test_concurrency.py) esto rompe
    # `ORDER BY created_at DESC` como criterio de "última entrada" del
    # Stock Ledger. `id` (UUID aleatorio) tampoco sirve de desempate.
    # `entry_seq` usa una SEQUENCE real de PostgreSQL (`nextval()`,
    # evaluado en el momento real del INSERT) como único criterio
    # monotónico confiable.
    op.execute("CREATE SEQUENCE stock_ledger_entries_seq")
    op.add_column(
        "stock_ledger_entries",
        sa.Column(
            "entry_seq",
            sa.BigInteger(),
            server_default=sa.text("nextval('stock_ledger_entries_seq')"),
            nullable=False,
        ),
    )
    op.execute("ALTER SEQUENCE stock_ledger_entries_seq OWNED BY stock_ledger_entries.entry_seq")
    op.create_unique_constraint(
        "uq_stock_ledger_entries_entry_seq", "stock_ledger_entries", ["entry_seq"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_stock_ledger_entries_entry_seq", "stock_ledger_entries", type_="unique"
    )
    op.drop_column("stock_ledger_entries", "entry_seq")
    op.execute("DROP SEQUENCE IF EXISTS stock_ledger_entries_seq")
