"""Link contractual invoices and configure asset disposal accounts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None

_safe_add = "IF NOT EXISTS"


def _col_exists(conn, table: str, column: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c)"
        ),
        {"t": table, "c": column},
    ).scalar()


def _fk_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name=:n)"
        ),
        {"n": name},
    ).scalar()


def _idx_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text("SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname=:n)"),
        {"n": name},
    ).scalar()


def upgrade() -> None:
    bind = op.get_bind()

    for table, col in [
        ("companies", "asset_disposal_gain_account_id"),
        ("companies", "asset_disposal_loss_account_id"),
        ("companies", "inventory_account_id"),
        ("companies", "inventory_adjustment_gain_account_id"),
        ("companies", "inventory_adjustment_loss_account_id"),
        ("supplier_invoices", "contract_installment_id"),
    ]:
        if not _col_exists(bind, table, col):
            op.add_column(table, sa.Column(col, postgresql.UUID(as_uuid=True), nullable=True))

    if not _fk_exists(bind, "fk_supplier_invoice_contract_installment"):
        op.create_foreign_key(
            "fk_supplier_invoice_contract_installment",
            "supplier_invoices",
            "contract_payment_installments",
            ["contract_installment_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    if not _idx_exists(bind, "uq_supplier_invoice_contract_installment"):
        op.create_index(
            "uq_supplier_invoice_contract_installment",
            "supplier_invoices",
            ["contract_installment_id"],
            unique=True,
            postgresql_where=sa.text(
                "contract_installment_id IS NOT NULL AND status <> 'CANCELLED'"
            ),
        )


def downgrade() -> None:
    op.drop_index(
        "uq_supplier_invoice_contract_installment", table_name="supplier_invoices"
    )
    op.drop_constraint(
        "fk_supplier_invoice_contract_installment",
        "supplier_invoices",
        type_="foreignkey",
    )
    op.drop_column("supplier_invoices", "contract_installment_id")
    op.drop_column("companies", "asset_disposal_loss_account_id")
    op.drop_column("companies", "asset_disposal_gain_account_id")
    op.drop_column("companies", "inventory_adjustment_loss_account_id")
    op.drop_column("companies", "inventory_adjustment_gain_account_id")
    op.drop_column("companies", "inventory_account_id")
