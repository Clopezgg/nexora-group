"""voucher branding Evidence snapshots

Revision ID: f1a4c2d8e9b0
Revises: e7f2a9c14d58
Create Date: 2026-09-06

Closes DEFERRED-FINAL-020. A voucher freezes the company logo/signature
Evidence identifiers on first issuance, exactly like the existing textual
company snapshot. Evidence is immutable/private and validated in company
scope before it can be assigned to Company. No foreign keys are added here to
avoid a voucher/evidence lifecycle coupling; the snapshot is historical.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f1a4c2d8e9b0"
down_revision: Union[str, None] = "e7f2a9c14d58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voucher_issuances",
        sa.Column("company_logo_evidence_id_snapshot", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "voucher_issuances",
        sa.Column("company_signature_evidence_id_snapshot", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voucher_issuances", "company_signature_evidence_id_snapshot")
    op.drop_column("voucher_issuances", "company_logo_evidence_id_snapshot")
