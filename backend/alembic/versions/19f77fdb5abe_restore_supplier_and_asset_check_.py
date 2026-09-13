"""restore_supplier_and_asset_check_constraints

Revision ID: 19f77fdb5abe
Revises: adfb3df167f0
Create Date: 2026-09-11 14:20:21.670177

"""
from typing import Sequence, Union

from alembic import op

revision: str = '19f77fdb5abe'
down_revision: Union[str, None] = 'adfb3df167f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CREATE_CHECK = """\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}' AND conrelid = '{table}'::regclass) THEN
    ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr});
  END IF;
END $$;"""


def upgrade() -> None:
    op.execute(_CREATE_CHECK.format(
        name='ck_fixed_assets_accumulated_depreciation_non_negative',
        table='fixed_assets',
        expr='COALESCE(accumulated_depreciation, 0) >= 0',
    ))
    op.execute(_CREATE_CHECK.format(
        name='ck_fixed_assets_disposal_date',
        table='fixed_assets',
        expr="(status NOT IN ('DISPOSED','RETIRED')) OR disposal_date IS NOT NULL",
    ))
    op.execute(_CREATE_CHECK.format(
        name='ck_fixed_assets_disposal_proceeds_non_negative',
        table='fixed_assets',
        expr='COALESCE(disposal_proceeds, 0) >= 0',
    ))
    op.execute(_CREATE_CHECK.format(
        name='ck_suppliers_party_role',
        table='suppliers',
        expr="party_role IN ('SUPPLIER','CONTRACTOR','BOTH')",
    ))
    op.execute(_CREATE_CHECK.format(
        name='ck_suppliers_status',
        table='suppliers',
        expr="status IN ('ACTIVE','INACTIVE','BLOCKED','ARCHIVED')",
    ))


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_suppliers_status' AND conrelid = 'suppliers'::regclass) THEN
    ALTER TABLE suppliers DROP CONSTRAINT ck_suppliers_status;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_suppliers_party_role' AND conrelid = 'suppliers'::regclass) THEN
    ALTER TABLE suppliers DROP CONSTRAINT ck_suppliers_party_role;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fixed_assets_disposal_proceeds_non_negative' AND conrelid = 'fixed_assets'::regclass) THEN
    ALTER TABLE fixed_assets DROP CONSTRAINT ck_fixed_assets_disposal_proceeds_non_negative;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fixed_assets_disposal_date' AND conrelid = 'fixed_assets'::regclass) THEN
    ALTER TABLE fixed_assets DROP CONSTRAINT ck_fixed_assets_disposal_date;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fixed_assets_accumulated_depreciation_non_negative' AND conrelid = 'fixed_assets'::regclass) THEN
    ALTER TABLE fixed_assets DROP CONSTRAINT ck_fixed_assets_accumulated_depreciation_non_negative;
  END IF;
END $$;""")
