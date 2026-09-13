"""Make financial three-way matches invoice-authoritative and overridable."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
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


def _check_exists(conn, name: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name=:n AND constraint_type='CHECK')"
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

    for col, typ, nullable, default in [
        ("match_kind", sa.String(length=20), False, "LEGACY_PREVIEW"),
        ("override_reason", sa.String(length=1000), True, None),
        ("overridden_by_user_id", postgresql.UUID(as_uuid=True), True, None),
        ("overridden_at", sa.DateTime(timezone=True), True, None),
        ("override_evidence_id", postgresql.UUID(as_uuid=True), True, None),
    ]:
        if not _col_exists(bind, "three_way_match_results", col):
            if default is not None:
                op.add_column(
                    "three_way_match_results",
                    sa.Column(col, typ, nullable=nullable, server_default=default),
                )
            else:
                op.add_column(
                    "three_way_match_results", sa.Column(col, typ, nullable=nullable)
                )

    if not _fk_exists(bind, "fk_twm_overridden_by_user"):
        op.create_foreign_key(
            "fk_twm_overridden_by_user",
            "three_way_match_results",
            "users",
            ["overridden_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    if not _fk_exists(bind, "fk_twm_override_evidence"):
        op.create_foreign_key(
            "fk_twm_override_evidence",
            "three_way_match_results",
            "evidence",
            ["override_evidence_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    if not _check_exists(bind, "ck_twm_financial_invoice_required"):
        op.create_check_constraint(
            "ck_twm_financial_invoice_required",
            "three_way_match_results",
            "match_kind = 'LEGACY_PREVIEW' OR "
            "(match_kind = 'FINANCIAL' AND supplier_invoice_id IS NOT NULL)",
        )
    if not _check_exists(bind, "ck_twm_override_complete"):
        op.create_check_constraint(
            "ck_twm_override_complete",
            "three_way_match_results",
            "(override_reason IS NULL AND overridden_by_user_id IS NULL AND overridden_at IS NULL) OR "
            "(status = 'EXCEPTION' AND override_reason IS NOT NULL "
            "AND overridden_by_user_id IS NOT NULL AND overridden_at IS NOT NULL)",
        )
    if not _idx_exists(bind, "uq_twm_financial_supplier_invoice"):
        op.create_index(
            "uq_twm_financial_supplier_invoice",
            "three_way_match_results",
            ["supplier_invoice_id"],
            unique=True,
            postgresql_where=sa.text("match_kind = 'FINANCIAL'"),
        )
    if _col_exists(bind, "three_way_match_results", "match_kind"):
        op.alter_column(
            "three_way_match_results",
            "match_kind",
            server_default="FINANCIAL",
        )


def downgrade() -> None:
    op.drop_index("uq_twm_financial_supplier_invoice", table_name="three_way_match_results")
    op.drop_constraint("ck_twm_override_complete", "three_way_match_results", type_="check")
    op.drop_constraint("ck_twm_financial_invoice_required", "three_way_match_results", type_="check")
    op.drop_constraint("fk_twm_override_evidence", "three_way_match_results", type_="foreignkey")
    op.drop_constraint("fk_twm_overridden_by_user", "three_way_match_results", type_="foreignkey")
    op.drop_column("three_way_match_results", "override_evidence_id")
    op.drop_column("three_way_match_results", "overridden_at")
    op.drop_column("three_way_match_results", "overridden_by_user_id")
    op.drop_column("three_way_match_results", "override_reason")
    op.drop_column("three_way_match_results", "match_kind")
