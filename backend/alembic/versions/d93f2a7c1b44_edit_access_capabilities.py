"""persist finite protected-edit capabilities and security audit

Revision ID: d93f2a7c1b44
Revises: b41e7c9a2f10
Create Date: 2026-08-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d93f2a7c1b44"
down_revision: Union[str, None] = "b41e7c9a2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "edit_access_capabilities",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uses_remaining", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("uses_remaining >= 0", name="ck_edit_access_capability_uses_non_negative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_edit_access_capabilities_user_id"), "edit_access_capabilities", ["user_id"], unique=False)
    op.create_index(op.f("ix_edit_access_capabilities_expires_at"), "edit_access_capabilities", ["expires_at"], unique=False)

    op.create_table(
        "edit_access_events",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_edit_access_events_user_id"), "edit_access_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_edit_access_events_created_at"), "edit_access_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_edit_access_events_created_at"), table_name="edit_access_events")
    op.drop_index(op.f("ix_edit_access_events_user_id"), table_name="edit_access_events")
    op.drop_table("edit_access_events")
    op.drop_index(op.f("ix_edit_access_capabilities_expires_at"), table_name="edit_access_capabilities")
    op.drop_index(op.f("ix_edit_access_capabilities_user_id"), table_name="edit_access_capabilities")
    op.drop_table("edit_access_capabilities")
