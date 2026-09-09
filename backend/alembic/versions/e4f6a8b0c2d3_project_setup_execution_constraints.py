"""add project setup execution state constraints

Revision ID: e4f6a8b0c2d3
Revises: d3e5f7a9b1c2
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e4f6a8b0c2d3"
down_revision: Union[str, None] = "d3e5f7a9b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_project_setup_runs_valid_status",
        "project_setup_runs",
        "status IN ('DRAFT', 'EXECUTING', 'COMPLETED', 'FAILED')",
    )
    op.create_unique_constraint(
        "uq_project_setup_runs_project", "project_setup_runs", ["project_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_project_setup_runs_project", "project_setup_runs", type_="unique")
    op.drop_constraint("ck_project_setup_runs_valid_status", "project_setup_runs", type_="check")
