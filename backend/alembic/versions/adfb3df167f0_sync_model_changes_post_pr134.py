"""sync_model_changes_post_pr134

Revision ID: adfb3df167f0
Revises: f2c3d4e5f6a7
Create Date: 2026-09-11 13:57:51.715373

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'adfb3df167f0'
down_revision: Union[str, None] = 'f2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DROP_CONSTRAINT = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}' AND conrelid = '{table}'::regclass) THEN
    ALTER TABLE {table} DROP CONSTRAINT {name};
  END IF;
END $$;"""

_DROP_INDEX = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = '{name}' AND tablename = '{table}') THEN
    DROP INDEX {name};
  END IF;
END $$;"""

_DROP_COL = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = '{table}' AND column_name = '{col}') THEN
    ALTER TABLE {table} DROP COLUMN {col};
  END IF;
END $$;"""


def upgrade() -> None:
    op.execute(_DROP_CONSTRAINT.format(name='fk_companies_logo_evidence', table='companies'))
    op.execute(_DROP_CONSTRAINT.format(name='fk_companies_signature_evidence', table='companies'))
    op.execute(_DROP_CONSTRAINT.format(name='ck_fixed_assets_accumulated_depreciation_non_negative', table='fixed_assets'))
    op.execute(_DROP_CONSTRAINT.format(name='ck_fixed_assets_disposal_date', table='fixed_assets'))
    op.execute(_DROP_CONSTRAINT.format(name='ck_fixed_assets_disposal_proceeds_non_negative', table='fixed_assets'))
    op.execute(_DROP_CONSTRAINT.format(name='fk_physical_counts_inventory_account', table='physical_counts'))
    op.execute(_DROP_CONSTRAINT.format(name='fk_physical_counts_adjustment_gain_account', table='physical_counts'))
    op.execute(_DROP_CONSTRAINT.format(name='fk_physical_counts_adjustment_loss_account', table='physical_counts'))
    op.execute(_DROP_COL.format(table='physical_counts', col='adjustment_gain_account_id'))
    op.execute(_DROP_COL.format(table='physical_counts', col='inventory_account_id'))
    op.execute(_DROP_COL.format(table='physical_counts', col='adjustment_loss_account_id'))
    op.execute(_DROP_INDEX.format(name='ix_purchase_orders_supplier_contract_id', table='purchase_orders'))
    op.execute(_DROP_CONSTRAINT.format(name='ck_purchase_requisitions_priority_valid', table='purchase_requisitions'))
    op.execute(_DROP_INDEX.format(name='ix_supplier_invoice_plan_invoice', table='supplier_invoice_payment_plan_items'))
    op.execute(_DROP_CONSTRAINT.format(name='uq_supplier_invoice_plan_sequence', table='supplier_invoice_payment_plan_items'))
    op.execute(_DROP_INDEX.format(name='ix_supplier_invoices_purchase_order_id', table='supplier_invoices'))
    op.execute(_DROP_INDEX.format(name='ix_supplier_invoices_supplier_contract_id', table='supplier_invoices'))
    op.execute(_DROP_CONSTRAINT.format(name='ck_suppliers_party_role', table='suppliers'))
    op.execute(_DROP_CONSTRAINT.format(name='ck_suppliers_status', table='suppliers'))


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_suppliers_status' AND conrelid = 'suppliers'::regclass) THEN
    ALTER TABLE suppliers ADD CONSTRAINT ck_suppliers_status CHECK (status IN ('ACTIVE','INACTIVE','BLOCKED','ARCHIVED'));
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_suppliers_party_role' AND conrelid = 'suppliers'::regclass) THEN
    ALTER TABLE suppliers ADD CONSTRAINT ck_suppliers_party_role CHECK (party_role IN ('SUPPLIER','CONTRACTOR','BOTH'));
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_supplier_invoices_supplier_contract_id') THEN
    CREATE INDEX ix_supplier_invoices_supplier_contract_id ON supplier_invoices (supplier_contract_id);
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_supplier_invoices_purchase_order_id') THEN
    CREATE INDEX ix_supplier_invoices_purchase_order_id ON supplier_invoices (purchase_order_id);
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_supplier_invoice_plan_sequence' AND conrelid = 'supplier_invoice_payment_plan_items'::regclass) THEN
    ALTER TABLE supplier_invoice_payment_plan_items ADD CONSTRAINT uq_supplier_invoice_plan_sequence UNIQUE (supplier_invoice_id, sequence);
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_supplier_invoice_plan_invoice') THEN
    CREATE INDEX ix_supplier_invoice_plan_invoice ON supplier_invoice_payment_plan_items (supplier_invoice_id);
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_purchase_requisitions_priority_valid' AND conrelid = 'purchase_requisitions'::regclass) THEN
    ALTER TABLE purchase_requisitions ADD CONSTRAINT ck_purchase_requisitions_priority_valid CHECK (priority IN ('LOW','NORMAL','HIGH','URGENT'));
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_purchase_orders_supplier_contract_id') THEN
    CREATE INDEX ix_purchase_orders_supplier_contract_id ON purchase_orders (supplier_contract_id);
  END IF;
END $$;""")
    conn = op.get_bind()
    if not conn.execute(sa.text("SELECT 1 FROM information_schema.columns WHERE table_name='physical_counts' AND column_name='adjustment_loss_account_id'")).fetchone():
        op.add_column('physical_counts', sa.Column('adjustment_loss_account_id', sa.UUID(), autoincrement=False, nullable=True))
    if not conn.execute(sa.text("SELECT 1 FROM information_schema.columns WHERE table_name='physical_counts' AND column_name='inventory_account_id'")).fetchone():
        op.add_column('physical_counts', sa.Column('inventory_account_id', sa.UUID(), autoincrement=False, nullable=True))
    if not conn.execute(sa.text("SELECT 1 FROM information_schema.columns WHERE table_name='physical_counts' AND column_name='adjustment_gain_account_id'")).fetchone():
        op.add_column('physical_counts', sa.Column('adjustment_gain_account_id', sa.UUID(), autoincrement=False, nullable=True))
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_physical_counts_adjustment_loss_account' AND conrelid = 'physical_counts'::regclass) THEN
    ALTER TABLE physical_counts ADD CONSTRAINT fk_physical_counts_adjustment_loss_account FOREIGN KEY (adjustment_loss_account_id) REFERENCES accounts(id) ON DELETE RESTRICT;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_physical_counts_adjustment_gain_account' AND conrelid = 'physical_counts'::regclass) THEN
    ALTER TABLE physical_counts ADD CONSTRAINT fk_physical_counts_adjustment_gain_account FOREIGN KEY (adjustment_gain_account_id) REFERENCES accounts(id) ON DELETE RESTRICT;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_physical_counts_inventory_account' AND conrelid = 'physical_counts'::regclass) THEN
    ALTER TABLE physical_counts ADD CONSTRAINT fk_physical_counts_inventory_account FOREIGN KEY (inventory_account_id) REFERENCES accounts(id) ON DELETE RESTRICT;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fixed_assets_disposal_proceeds_non_negative' AND conrelid = 'fixed_assets'::regclass) THEN
    ALTER TABLE fixed_assets ADD CONSTRAINT ck_fixed_assets_disposal_proceeds_non_negative CHECK (COALESCE(disposal_proceeds, 0) >= 0);
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fixed_assets_disposal_date' AND conrelid = 'fixed_assets'::regclass) THEN
    ALTER TABLE fixed_assets ADD CONSTRAINT ck_fixed_assets_disposal_date CHECK ((status NOT IN ('DISPOSED','RETIRED')) OR disposal_date IS NOT NULL);
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fixed_assets_accumulated_depreciation_non_negative' AND conrelid = 'fixed_assets'::regclass) THEN
    ALTER TABLE fixed_assets ADD CONSTRAINT ck_fixed_assets_accumulated_depreciation_non_negative CHECK (COALESCE(accumulated_depreciation, 0) >= 0);
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_companies_signature_evidence' AND conrelid = 'companies'::regclass) THEN
    ALTER TABLE companies ADD CONSTRAINT fk_companies_signature_evidence FOREIGN KEY (signature_evidence_id) REFERENCES evidence(id) ON DELETE SET NULL;
  END IF;
END $$;""")
    op.execute("""DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_companies_logo_evidence' AND conrelid = 'companies'::regclass) THEN
    ALTER TABLE companies ADD CONSTRAINT fk_companies_logo_evidence FOREIGN KEY (logo_evidence_id) REFERENCES evidence(id) ON DELETE SET NULL;
  END IF;
END $$;""")
