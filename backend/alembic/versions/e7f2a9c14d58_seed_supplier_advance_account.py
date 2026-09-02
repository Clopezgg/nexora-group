"""seed a canonical supplier-advance ASSET account per company

Revision ID: e7f2a9c14d58
Revises: d4b9f1c07e33
Create Date: 2026-09-02

ORDEN MAESTRA DE CIERRE §7/§23 — la reclasificación de un anticipo contractual
hacia un ACTIVO (prepago) exige que la compañía tenga configurada una cuenta
``supplier_advance_account_id`` (ASSET, postable). El dataset productivo DEV se
creó sin esa cuenta, de modo que ni el registro normal de anticipos de contrato
(``contract_payments``) ni la reconciliación del anticipo duplicado L50k pueden
operar.

Esta migración es estructural (plan de cuentas), no una cifra financiera
hardcodeada, e idempotente:

* para cada ``chart_of_accounts`` que aún no tenga una cuenta de anticipos a
  proveedores/contratistas (código ``1202`` o nombre que contenga
  "anticip" + "proveedor"/"contratista"), crea
  ``1202 — Anticipos a proveedores y contratistas`` (ASSET, postable), colgada
  de la cuenta agrupadora de activos (``1000``) si existe;
* para cada compañía con ``supplier_advance_account_id IS NULL``, la apunta a
  esa cuenta.

No toca ninguna compañía que ya tenga la cuenta o el selector configurado.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "e7f2a9c14d58"
down_revision: Union[str, None] = "d4b9f1c07e33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ADVANCE_CODE = "1202"
_ADVANCE_NAME = "Anticipos a proveedores y contratistas"


def upgrade() -> None:
    conn = op.get_bind()

    charts = conn.exec_driver_sql("SELECT id, company_id FROM chart_of_accounts").fetchall()
    for chart_id, company_id in charts:
        existing = conn.exec_driver_sql(
            """
            SELECT id FROM accounts
            WHERE chart_of_account_id = %(chart)s
              AND account_type = 'ASSET'
              AND (
                    code = %(code)s
                 OR (lower(name) LIKE '%%anticip%%'
                     AND (lower(name) LIKE '%%proveedor%%' OR lower(name) LIKE '%%contratista%%'))
              )
            ORDER BY code
            LIMIT 1
            """,
            {"chart": chart_id, "code": _ADVANCE_CODE},
        ).fetchone()

        if existing is not None:
            account_id = existing[0]
        else:
            # avoid colliding with an existing code 1202 of another type
            code = _ADVANCE_CODE
            clash = conn.exec_driver_sql(
                "SELECT 1 FROM accounts WHERE chart_of_account_id = %(chart)s AND code = %(code)s",
                {"chart": chart_id, "code": code},
            ).fetchone()
            if clash is not None:
                code = "1402"
            parent = conn.exec_driver_sql(
                "SELECT id FROM accounts WHERE chart_of_account_id = %(chart)s AND code = '1000' LIMIT 1",
                {"chart": chart_id},
            ).fetchone()
            parent_id = parent[0] if parent is not None else None
            account_id = conn.exec_driver_sql(
                """
                INSERT INTO accounts
                    (id, chart_of_account_id, code, name, account_type, parent_id,
                     is_postable, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), %(chart)s, %(code)s, %(name)s, 'ASSET', %(parent)s,
                     TRUE, now(), now())
                RETURNING id
                """,
                {"chart": chart_id, "code": code, "name": _ADVANCE_NAME, "parent": parent_id},
            ).fetchone()[0]

        conn.exec_driver_sql(
            """
            UPDATE companies
               SET supplier_advance_account_id = %(account)s
             WHERE id = %(company)s
               AND supplier_advance_account_id IS NULL
            """,
            {"account": account_id, "company": company_id},
        )


def downgrade() -> None:
    # Structural, idempotent seed. Nulling the selector or dropping the account
    # could strand posted journal lines; downgrade is intentionally a no-op.
    pass
