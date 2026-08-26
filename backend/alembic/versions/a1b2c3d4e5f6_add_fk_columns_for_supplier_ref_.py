"""Add FK columns for MaintenanceOrder.supplier_id and Project.customer_id

DEFERRED-FINAL-012: converts free-text supplier_ref/customer_ref to proper
FK references now that Supplier and Customer entities exist.

Revision ID: a1b2c3d4e5f6
Revises: f66768a419c3
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f1efb082cb0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "maintenance_orders",
        sa.Column("supplier_id", sa.UUID(), sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "customer_id")
    op.drop_column("maintenance_orders", "supplier_id")
