"""store physical-count GL account configuration

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
"""

from alembic import op
import sqlalchemy as sa


revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("physical_counts", sa.Column("inventory_account_id", sa.UUID(), nullable=True))
    op.add_column("physical_counts", sa.Column("adjustment_gain_account_id", sa.UUID(), nullable=True))
    op.add_column("physical_counts", sa.Column("adjustment_loss_account_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_physical_counts_inventory_account", "physical_counts", "accounts", ["inventory_account_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_physical_counts_adjustment_gain_account", "physical_counts", "accounts", ["adjustment_gain_account_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_physical_counts_adjustment_loss_account", "physical_counts", "accounts", ["adjustment_loss_account_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    op.drop_constraint("fk_physical_counts_adjustment_loss_account", "physical_counts", type_="foreignkey")
    op.drop_constraint("fk_physical_counts_adjustment_gain_account", "physical_counts", type_="foreignkey")
    op.drop_constraint("fk_physical_counts_inventory_account", "physical_counts", type_="foreignkey")
    op.drop_column("physical_counts", "adjustment_loss_account_id")
    op.drop_column("physical_counts", "adjustment_gain_account_id")
    op.drop_column("physical_counts", "inventory_account_id")
