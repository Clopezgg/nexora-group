"""Prevent duplicate supplier invitations and quotation reuse."""

import sqlalchemy as sa

from alembic import op

revision = "f2c3d4e5f6a7"
down_revision = "f1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column(
            "fulfillment_type",
            sa.String(length=16),
            nullable=False,
            server_default="GOODS",
        ),
    )
    op.create_check_constraint(
        "ck_purchase_orders_fulfillment_type_valid",
        "purchase_orders",
        "fulfillment_type IN ('GOODS','SERVICE')",
    )
    op.create_unique_constraint(
        "uq_rfq_suppliers_invitation",
        "rfq_suppliers",
        ["request_for_quotation_id", "supplier_id"],
    )
    op.create_unique_constraint(
        "uq_purchase_orders_supplier_quotation",
        "purchase_orders",
        ["supplier_quotation_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_purchase_orders_supplier_quotation", "purchase_orders", type_="unique"
    )
    op.drop_constraint(
        "uq_rfq_suppliers_invitation", "rfq_suppliers", type_="unique"
    )
    op.drop_constraint(
        "ck_purchase_orders_fulfillment_type_valid", "purchase_orders", type_="check"
    )
    op.drop_column("purchase_orders", "fulfillment_type")
