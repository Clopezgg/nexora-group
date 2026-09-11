"""Prevent duplicate supplier invitations and quotation reuse."""

import sqlalchemy as sa

from alembic import op

revision = "f2c3d4e5f6a7"
down_revision = "f1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c)"
        ),
        {"t": table, "c": column},
    ).scalar()


def _check_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name=:n AND constraint_type='CHECK')"
        ),
        {"n": name},
    ).scalar()


def _unique_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name=:n AND constraint_type='UNIQUE')"
        ),
        {"n": name},
    ).scalar()


def upgrade() -> None:
    bind = op.get_bind()

    if not _col_exists(bind, "purchase_orders", "fulfillment_type"):
        op.add_column(
            "purchase_orders",
            sa.Column(
                "fulfillment_type",
                sa.String(length=16),
                nullable=False,
                server_default="GOODS",
            ),
        )
    if not _check_exists(bind, "ck_purchase_orders_fulfillment_type_valid"):
        op.create_check_constraint(
            "ck_purchase_orders_fulfillment_type_valid",
            "purchase_orders",
            "fulfillment_type IN ('GOODS','SERVICE')",
        )
    if not _unique_exists(bind, "uq_rfq_suppliers_invitation"):
        op.create_unique_constraint(
            "uq_rfq_suppliers_invitation",
            "rfq_suppliers",
            ["request_for_quotation_id", "supplier_id"],
        )
    if not _unique_exists(bind, "uq_purchase_orders_supplier_quotation"):
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
