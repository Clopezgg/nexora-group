"""reset the two explicitly authorized initial projects

Revision ID: b41e7c9a2f10
Revises: 9c6d4b2a1e70
Create Date: 2026-08-28

The owner explicitly requested removal of the two initial planning projects so
NEXORA starts with an empty project workspace. The migration is deliberately
narrow and safety-first: it only targets the exact project code/name pairs and
refuses to run if any RESTRICT/NO ACTION foreign-key reference exists. This
prevents deleting a project that acquired financial or operational history
between authorization and deployment.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b41e7c9a2f10"
down_revision: Union[str, None] = "9c6d4b2a1e70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TARGET_PREDICATE = """
(
  (p.code = '21000' AND p.name = 'Cerco Perimetral')
  OR
  (p.code = '22000' AND p.name = 'Portones y Verjas')
)
"""


def upgrade() -> None:
    # Abort rather than destroy history if either project has gained a row in
    # any table whose FK policy intentionally forbids project deletion.
    op.execute(
        f"""
        DO $$
        DECLARE
          ref RECORD;
          conflict_count BIGINT;
        BEGIN
          FOR ref IN
            SELECT
              tc.table_schema,
              tc.table_name,
              kcu.column_name,
              rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.constraint_schema = kcu.constraint_schema
            JOIN information_schema.referential_constraints rc
              ON tc.constraint_name = rc.constraint_name
             AND tc.constraint_schema = rc.constraint_schema
            JOIN information_schema.constraint_column_usage ccu
              ON rc.unique_constraint_name = ccu.constraint_name
             AND rc.unique_constraint_schema = ccu.constraint_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'projects'
              AND rc.delete_rule IN ('NO ACTION', 'RESTRICT')
          LOOP
            EXECUTE format(
              'SELECT count(*) FROM %I.%I r WHERE r.%I IN '
              || '(SELECT p.id FROM projects p JOIN companies c ON c.id = p.company_id '
              || 'WHERE upper(c.name) = ''NEXORA GROUP'' AND {predicate})',
              ref.table_schema,
              ref.table_name,
              ref.column_name
            ) INTO conflict_count;

            IF conflict_count > 0 THEN
              RAISE EXCEPTION
                'Project reset blocked safely: %.% contains % protected reference(s)',
                ref.table_schema, ref.table_name, conflict_count;
            END IF;
          END LOOP;
        END $$;
        """.replace("{{predicate}}", _TARGET_PREDICATE.replace("\n", " "))
    )

    # Cascading project-control records (for example WBS/budgets) are removed
    # by their published FK policies; SET NULL relationships preserve audit
    # and contextual history. No company/account/treasury master data is touched.
    op.execute(
        f"""
        DELETE FROM projects p
        USING companies c
        WHERE p.company_id = c.id
          AND upper(c.name) = 'NEXORA GROUP'
          AND {_TARGET_PREDICATE};
        """
    )


def downgrade() -> None:
    # Destructive business-data resets cannot be reconstructed truthfully from
    # schema history alone. Recreating invented project/budget data would violate
    # NEXORA's no-fake-data invariant, so downgrade intentionally does nothing.
    pass
