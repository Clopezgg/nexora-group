"""Enforce service acceptance controls and persist its TWM receipt basis."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "f1b2c3d4e5f6"
down_revision = "f0a1b2c3d4e5"
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

    if _check_exists(bind, "ck_service_entries_progress_valid"):
        op.drop_constraint(
            "ck_service_entries_progress_valid", "service_entries", type_="check"
        )
    if _check_exists(bind, "ck_service_entries_value_non_negative"):
        op.drop_constraint(
            "ck_service_entries_value_non_negative", "service_entries", type_="check"
        )

    op.create_check_constraint(
        "ck_service_entries_progress_valid",
        "service_entries",
        "progress_percentage > 0 AND progress_percentage <= 100",
    )
    op.create_check_constraint(
        "ck_service_entries_value_positive", "service_entries", "accepted_value > 0"
    )
    op.create_check_constraint(
        "ck_service_entries_period_valid", "service_entries", "period_start <= period_end"
    )

    if not _col_exists(bind, "service_entries", "evidence_id"):
        op.add_column(
            "service_entries",
            sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if not _fk_exists(bind, "fk_service_entries_evidence"):
        op.create_foreign_key(
            "fk_service_entries_evidence",
            "service_entries",
            "evidence",
            ["evidence_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    if not _col_exists(bind, "three_way_match_results", "receipt_basis"):
        op.add_column(
            "three_way_match_results",
            sa.Column(
                "receipt_basis",
                sa.String(length=24),
                nullable=False,
                server_default="GOODS_RECEIPT",
            ),
        )
    if not _col_exists(bind, "three_way_match_results", "accepted_amount"):
        op.add_column(
            "three_way_match_results",
            sa.Column(
                "accepted_amount",
                sa.Numeric(precision=18, scale=2),
                nullable=False,
                server_default="0",
            ),
        )
        op.execute(
            "UPDATE three_way_match_results SET accepted_amount = ordered_amount"
        )
        op.alter_column("three_way_match_results", "receipt_basis", server_default=None)
        op.alter_column("three_way_match_results", "accepted_amount", server_default=None)


def downgrade() -> None:
    op.drop_column("three_way_match_results", "accepted_amount")
    op.drop_column("three_way_match_results", "receipt_basis")
    op.drop_constraint(
        "fk_service_entries_evidence", "service_entries", type_="foreignkey"
    )
    op.drop_column("service_entries", "evidence_id")
    op.drop_constraint(
        "ck_service_entries_period_valid", "service_entries", type_="check"
    )
    op.drop_constraint(
        "ck_service_entries_value_positive", "service_entries", type_="check"
    )
    op.drop_constraint(
        "ck_service_entries_progress_valid", "service_entries", type_="check"
    )
    op.create_check_constraint(
        "ck_service_entries_progress_valid",
        "service_entries",
        "progress_percentage >= 0 AND progress_percentage <= 100",
    )
    op.create_check_constraint(
        "ck_service_entries_value_non_negative",
        "service_entries",
        "accepted_value >= 0",
    )
