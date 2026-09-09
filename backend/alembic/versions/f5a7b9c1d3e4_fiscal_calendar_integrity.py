"""Enforce unambiguous fiscal calendars and company/year identity.

Revision ID: f5a7b9c1d3e4
Revises: e4f6a8b0c2d3
"""

from alembic import op
import sqlalchemy as sa

revision = "f5a7b9c1d3e4"
down_revision = "e4f6a8b0c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Prevent concurrent calendar writes between preflight and constraint creation.
    op.execute("LOCK TABLE fiscal_years, fiscal_periods IN ACCESS EXCLUSIVE MODE")
    connection = op.get_bind()
    for table in ("fiscal_years", "fiscal_periods"):
        invalid = connection.execute(
            sa.text(f"""
            SELECT EXISTS (
                SELECT 1 FROM {table} a JOIN {table} b
                ON a.company_id = b.company_id AND a.id < b.id
                AND a.start_date <= b.end_date AND b.start_date <= a.end_date
            )
        """)
        ).scalar_one()
        if invalid:
            raise RuntimeError(
                f"{table}: overlapping fiscal ranges; resolve explicitly before upgrade"
            )
    mismatch = connection.execute(
        sa.text("""
        SELECT EXISTS (SELECT 1 FROM fiscal_periods p JOIN fiscal_years y
        ON y.id = p.fiscal_year_id WHERE p.company_id <> y.company_id)
    """)
    ).scalar_one()
    if mismatch:
        raise RuntimeError(
            "fiscal_periods: company/year mismatch; resolve explicitly before upgrade"
        )
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_unique_constraint(
        "uq_fiscal_years_id_company", "fiscal_years", ["id", "company_id"]
    )
    op.create_foreign_key(
        "fk_fiscal_periods_year_company",
        "fiscal_periods",
        "fiscal_years",
        ["fiscal_year_id", "company_id"],
        ["id", "company_id"],
        ondelete="CASCADE",
    )
    for table in ("fiscal_years", "fiscal_periods"):
        op.execute(f"""ALTER TABLE {table} ADD CONSTRAINT ex_{table}_company_dates
            EXCLUDE USING gist (company_id WITH =, daterange(start_date, end_date, '[]') WITH &&)""")


def downgrade() -> None:
    for table in ("fiscal_periods", "fiscal_years"):
        op.drop_constraint(f"ex_{table}_company_dates", table)
    op.drop_constraint(
        "fk_fiscal_periods_year_company", "fiscal_periods", type_="foreignkey"
    )
    op.drop_constraint("uq_fiscal_years_id_company", "fiscal_years", type_="unique")
    # btree_gist may serve other schemas: do not remove shared infrastructure.
