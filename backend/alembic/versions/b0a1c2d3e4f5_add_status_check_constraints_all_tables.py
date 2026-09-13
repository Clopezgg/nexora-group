"""add_status_check_constraints_all_tables

Revision ID: b0a1c2d3e4f5
Revises: 19f77fdb5abe
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'b0a1c2d3e4f5'
down_revision: Union[str, None] = '19f77fdb5abe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHECK_EXISTS = """\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}' AND conrelid = '{table}'::regclass) THEN
    ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr});
  END IF;
END $$;"""

_CHECK_EXISTS_ALSO = """\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}' AND conrelid = '{table}'::regclass) THEN
    ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr});
  END IF;
END $$;"""


def upgrade() -> None:
    # P0 - Critical financial/lifecycle tables
    op.execute(_CHECK_EXISTS.format(
        name='ck_accounting_documents_status_valid',
        table='accounting_documents',
        expr="status IN ('DRAFT','POSTED','REVERSED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_supplier_invoices_status_valid',
        table='supplier_invoices',
        expr="status IN ('DRAFT','REVIEW','APPROVED','SCHEDULED','PARTIALLY_PAID','PAID','RECONCILED','CANCELLED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_customer_invoices_status_valid',
        table='customer_invoices',
        expr="status IN ('DRAFT','APPROVED','PARTIALLY_COLLECTED','COLLECTED','CANCELLED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_projects_status_valid',
        table='projects',
        expr="status IN ('PLANNING','ACTIVE','ON_HOLD','COMPLETED','CLOSED','CANCELLED','ARCHIVED')",
    ))

    # P1 - Domain tables
    op.execute(_CHECK_EXISTS.format(
        name='ck_supplier_contracts_status_valid',
        table='supplier_contracts',
        expr="status IN ('DRAFT','ACTIVE','COMPLETED','TERMINATED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_change_orders_status_valid',
        table='change_orders',
        expr="status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','IMPLEMENTED','CANCELLED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_wbs_nodes_status_valid',
        table='wbs_nodes',
        expr="status IN ('PLANNED','ACTIVE','ON_HOLD','COMPLETED','CANCELLED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_physical_counts_status_valid',
        table='physical_counts',
        expr="status IN ('DRAFT','COUNTED','APPROVED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_contract_payment_installments_status_valid',
        table='contract_payment_installments',
        expr="status IN ('UPCOMING','DUE','PARTIALLY_PAID','PAID','OVERDUE','CANCELLED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_contract_payment_schedules_status_valid',
        table='contract_payment_schedules',
        expr="status IN ('ACTIVE','COMPLETED','CANCELLED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_approval_requests_status_valid',
        table='approval_requests',
        expr="status IN ('PENDING','APPROVED','REJECTED','CANCELLED','EXPIRED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_crews_status_valid',
        table='crews',
        expr="status IN ('ACTIVE','INACTIVE')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_customers_status_valid',
        table='customers',
        expr="status IN ('ACTIVE','INACTIVE','BLOCKED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_leads_status_valid',
        table='leads',
        expr="status IN ('NEW','QUALIFIED','CONVERTED','LOST')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_quotations_status_valid',
        table='quotations',
        expr="status IN ('DRAFT','SENT','ACCEPTED','REJECTED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_sales_contracts_status_valid',
        table='sales_contracts',
        expr="status IN ('ACTIVE','BILLED','CANCELLED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_idempotency_records_status_valid',
        table='idempotency_records',
        expr="status IN ('PENDING','COMPLETED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_voucher_issuances_status_valid',
        table='voucher_issuances',
        expr="status IN ('ISSUED','VOIDED')",
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_warehouses_status_valid',
        table='warehouses',
        expr="status IN ('ACTIVE','INACTIVE')",
    ))

    # Quantity range checks for physical_count_lines
    op.execute(_CHECK_EXISTS.format(
        name='ck_physical_count_lines_expected_quantity_non_negative',
        table='physical_count_lines',
        expr='expected_quantity >= 0',
    ))
    op.execute(_CHECK_EXISTS.format(
        name='ck_physical_count_lines_counted_quantity_non_negative',
        table='physical_count_lines',
        expr='counted_quantity >= 0',
    ))

    # Performance indexes on high-traffic FK columns
    op.execute("""\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_accounting_documents_project_id') THEN
    CREATE INDEX ix_accounting_documents_project_id ON accounting_documents (project_id) WHERE project_id IS NOT NULL;
  END IF;
END $$;""")
    op.execute("""\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_supplier_invoices_project_id') THEN
    CREATE INDEX ix_supplier_invoices_project_id ON supplier_invoices (project_id) WHERE project_id IS NOT NULL;
  END IF;
END $$;""")
    op.execute("""\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_customer_invoices_project_id') THEN
    CREATE INDEX ix_customer_invoices_project_id ON customer_invoices (project_id) WHERE project_id IS NOT NULL;
  END IF;
END $$;""")
    op.execute("""\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_change_orders_project_id') THEN
    CREATE INDEX ix_change_orders_project_id ON change_orders (project_id);
  END IF;
END $$;""")
    op.execute("""\
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_approval_requests_company_id') THEN
    CREATE INDEX ix_approval_requests_company_id ON approval_requests (company_id);
  END IF;
END $$;""")


def downgrade() -> None:
    for idx in [
        'ix_approval_requests_company_id',
        'ix_change_orders_project_id',
        'ix_customer_invoices_project_id',
        'ix_supplier_invoices_project_id',
        'ix_accounting_documents_project_id',
    ]:
        op.execute(f"DROP INDEX IF EXISTS {idx}")

    for name, table in [
        ('ck_physical_count_lines_counted_quantity_non_negative', 'physical_count_lines'),
        ('ck_physical_count_lines_expected_quantity_non_negative', 'physical_count_lines'),
        ('ck_warehouses_status_valid', 'warehouses'),
        ('ck_voucher_issuances_status_valid', 'voucher_issuances'),
        ('ck_idempotency_records_status_valid', 'idempotency_records'),
        ('ck_sales_contracts_status_valid', 'sales_contracts'),
        ('ck_quotations_status_valid', 'quotations'),
        ('ck_leads_status_valid', 'leads'),
        ('ck_customers_status_valid', 'customers'),
        ('ck_crews_status_valid', 'crews'),
        ('ck_approval_requests_status_valid', 'approval_requests'),
        ('ck_contract_payment_schedules_status_valid', 'contract_payment_schedules'),
        ('ck_contract_payment_installments_status_valid', 'contract_payment_installments'),
        ('ck_physical_counts_status_valid', 'physical_counts'),
        ('ck_wbs_nodes_status_valid', 'wbs_nodes'),
        ('ck_change_orders_status_valid', 'change_orders'),
        ('ck_supplier_contracts_status_valid', 'supplier_contracts'),
        ('ck_projects_status_valid', 'projects'),
        ('ck_customer_invoices_status_valid', 'customer_invoices'),
        ('ck_supplier_invoices_status_valid', 'supplier_invoices'),
        ('ck_accounting_documents_status_valid', 'accounting_documents'),
    ]:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
