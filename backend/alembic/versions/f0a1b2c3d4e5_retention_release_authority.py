"""Persist formal authorization metadata for contractual retention releases."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f0a1b2c3d4e5"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contract_payment_installments",
        sa.Column("retention_release_reason", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "contract_payment_installments",
        sa.Column("retention_released_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "contract_payment_installments",
        sa.Column("retention_released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "contract_payment_installments",
        sa.Column("retention_release_evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_contract_retention_released_by",
        "contract_payment_installments",
        "users",
        ["retention_released_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
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
