"""supplier_contracts.contract_category + número de contrato único por compañía + projects.manager_user_id

Revision ID: b2d4f6a80c33
Revises: a1c3e5f70b21
Create Date: 2026-09-01

ORDEN MAESTRA DEFINITIVA DE INTEGRACIÓN §13/§15/§16.

- §13: `supplier_contracts.contract_category` — naturaleza del costo del
  contrato de ejecución (LABOR/SUBCONTRACT/MATERIALS/EQUIPMENT/
  PROFESSIONAL_SERVICES/OTHER). Backfill = 'OTHER' (dato existente sin
  categoría; el usuario la ajusta después). NOT NULL con server_default.
- §15: el número de contrato deja de ser globalmente único. Pasa a ser
  único POR COMPAÑÍA — dos compañías pueden tener su "C-001".
  `supplier_contracts` y `sales_contracts`.
- §16: `projects.manager_user_id` — responsable real como FK a users.
  El texto libre `projects.manager` se conserva. Backfill: se enlaza el
  usuario cuyo `full_name` o `email` coincide EXACTAMENTE (case-insensitive)
  con el texto — no se inventa una asignación.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2d4f6a80c33"
down_revision: Union[str, None] = "a1c3e5f70b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- §13: contract_category -------------------------------------------
    op.add_column(
        "supplier_contracts",
        sa.Column(
            "contract_category",
            sa.String(length=32),
            nullable=False,
            server_default="OTHER",
        ),
    )

    # --- §15: número de contrato único por compañía -----------------------
    # Los UNIQUE globales creados por `sa.UniqueConstraint('contract_number')`
    # reciben el nombre por defecto de PostgreSQL `<tabla>_<col>_key`.
    op.execute("ALTER TABLE supplier_contracts DROP CONSTRAINT IF EXISTS supplier_contracts_contract_number_key")
    op.execute("ALTER TABLE sales_contracts DROP CONSTRAINT IF EXISTS sales_contracts_contract_number_key")
    op.create_unique_constraint(
        "uq_supplier_contracts_company_number",
        "supplier_contracts",
        ["company_id", "contract_number"],
    )
    op.create_unique_constraint(
        "uq_sales_contracts_company_number",
        "sales_contracts",
        ["company_id", "contract_number"],
    )

    # --- §16: projects.manager_user_id -----------------------------------
    op.add_column(
        "projects",
        sa.Column("manager_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_projects_manager_user_id_users",
        "projects",
        "users",
        ["manager_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE projects p
        SET manager_user_id = u.id
        FROM users u
        WHERE p.manager IS NOT NULL
          AND p.manager <> ''
          AND (
            lower(btrim(p.manager)) = lower(btrim(u.full_name))
            OR lower(btrim(p.manager)) = lower(btrim(u.email))
          )
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_manager_user_id_users", "projects", type_="foreignkey")
    op.drop_column("projects", "manager_user_id")

    op.drop_constraint("uq_sales_contracts_company_number", "sales_contracts", type_="unique")
    op.drop_constraint(
        "uq_supplier_contracts_company_number", "supplier_contracts", type_="unique"
    )
    op.create_unique_constraint(
        "sales_contracts_contract_number_key", "sales_contracts", ["contract_number"]
    )
    op.create_unique_constraint(
        "supplier_contracts_contract_number_key",
        "supplier_contracts",
        ["contract_number"],
    )

    op.drop_column("supplier_contracts", "contract_category")
