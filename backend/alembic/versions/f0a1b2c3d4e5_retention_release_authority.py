"""Persist formal authorization metadata for contractual retention releases."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "f0a1b2c3d4e5"
down_revision = "e9f0a1b2c3d4"
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


def _fk_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name=:n)"
        ),
        {"n": name},
    ).scalar()


def upgrade() -> None:
    bind = op.get_bind()

    for col, typ, nullable in [
        ("retention_release_reason", sa.String(length=1000), True),
        ("retention_released_by_user_id", postgresql.UUID(as_uuid=True), True),
        ("retention_released_at", sa.DateTime(timezone=True), True),
        ("retention_release_evidence_id", postgresql.UUID(as_uuid=True), True),
    ]:
        if not _col_exists(bind, "contract_payment_installments", col):
            op.add_column(
                "contract_payment_installments", sa.Column(col, typ, nullable=nullable)
            )

    if not _fk_exists(bind, "fk_contract_retention_released_by"):
        op.create_foreign_key(
            "fk_contract_retention_released_by",
            "contract_payment_installments",
            "users",
            ["retention_released_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    if not _fk_exists(bind, "fk_contract_retention_release_evidence"):
        op.create_foreign_key(
            "fk_contract_retention_release_evidence",
            "contract_payment_installments",
            "evidence",
            ["retention_release_evidence_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_contract_retention_release_evidence",
        "contract_payment_installments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_contract_retention_released_by",
        "contract_payment_installments",
        type_="foreignkey",
    )
    op.drop_column("contract_payment_installments", "retention_release_evidence_id")
    op.drop_column("contract_payment_installments", "retention_released_at")
    op.drop_column("contract_payment_installments", "retention_released_by_user_id")
    op.drop_column("contract_payment_installments", "retention_release_reason")
