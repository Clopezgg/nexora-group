"""drop stale un-declared FK indexes

Closes model/migration drift: the SQLAlchemy models never declare standalone
indexes on these FK columns, so `alembic check` fails until the stale database
indexes are removed. Idempotent; reversible (re-creates a plain index).

Revision ID: eb8ce8e18b2d
Revises: b0a1c2d3e4f5
Create Date: 2026-09-12 20:45:05.348824

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'eb8ce8e18b2d'
down_revision: Union[str, None] = 'b0a1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STALE_INDEXES = (
    ("ix_accounting_documents_project_id", "accounting_documents", "project_id"),
    ("ix_approval_requests_company_id", "approval_requests", "company_id"),
    ("ix_change_orders_project_id", "change_orders", "project_id"),
    ("ix_customer_invoices_project_id", "customer_invoices", "project_id"),
    ("ix_supplier_invoices_project_id", "supplier_invoices", "project_id"),
)

_DROP_INDEX = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = '{name}' AND tablename = '{table}') THEN
    DROP INDEX {name};
  END IF;
END $$;"""

_CREATE_INDEX = """\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = '{name}' AND tablename = '{table}') THEN
    CREATE INDEX {name} ON {table} ({col});
  END IF;
END $$;"""


def upgrade() -> None:
    for name, table, _col in _STALE_INDEXES:
        op.execute(_DROP_INDEX.format(name=name, table=table))


def downgrade() -> None:
    for name, table, col in _STALE_INDEXES:
        op.execute(_CREATE_INDEX.format(name=name, table=table, col=col))