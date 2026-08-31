"""theme engine: user preferences + company defaults

Revision ID: f453d24d2120
Revises: 33941de1b1ae
Create Date: 2026-08-31

Orden maestra FINAL, Phase 8 (Enterprise Theme Engine). El tema es puramente
presentación (CLAUDE.md §68 / orden maestra §68): NUNCA afecta moneda,
cálculos, permisos, contabilidad, workflow ni estado de negocio. Aquí solo se
persiste la ELECCIÓN (un id de preset + densidad).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f453d24d2120"
down_revision: Union[str, None] = "33941de1b1ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("theme_id", sa.String(length=64), nullable=True),
        sa.Column("density", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column("companies", sa.Column("default_theme_id", sa.String(length=64), nullable=True))
    op.add_column("companies", sa.Column("default_density", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "default_density")
    op.drop_column("companies", "default_theme_id")
    op.drop_table("user_preferences")
