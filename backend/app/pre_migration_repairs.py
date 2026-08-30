"""Narrow pre-Alembic repairs for explicitly authorized legacy data resets.

This module exists because the published ``b41e7c9a2f10`` migration correctly
refuses to delete a project while a RESTRICT/NO ACTION reference exists.  The
production DEV dataset contains one legacy nullable supplier-contract link to
one of the two projects the owner explicitly asked to remove.

The repair is intentionally conservative:
- it runs only while the database is exactly at the migration immediately
  preceding the reset;
- it matches the exact company + project code + project name pairs;
- it only NULLs referencing columns that the schema declares nullable;
- it aborts the whole transaction if any mandatory reference exists;
- it records an append-only audit entry for each project before Alembic removes
  it and never deletes the referenced business documents themselves.

After ``b41e7c9a2f10`` is applied this becomes a permanent no-op.
"""

from __future__ import annotations

import json
import os
import uuid
from collections import defaultdict

import psycopg
from psycopg import sql

_PRE_RESET_REVISION = "9c6d4b2a1e70"
_TARGETS = (
    ("21000", "Cerco Perimetral"),
    ("22000", "Portones y Verjas"),
)
_CORRELATION_ID = "authorized-project-reset-2026-08-28"


def _dsn() -> str:
    value = os.environ.get("DATABASE_URL", "")
    if not value:
        raise RuntimeError("DATABASE_URL is required for pre-migration repair")
    return value.replace("postgresql+psycopg://", "postgresql://", 1)


def run_authorized_project_reset_preflight() -> None:
    """Detach only nullable RESTRICT references to the two authorized projects."""

    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.alembic_version')")
            if cur.fetchone()[0] is None:
                # Fresh database (e.g. Docker Compose smoke, first Azure
                # bootstrap): Alembic has not stamped a revision yet, so this
                # one-time legacy repair cannot apply. Let ``alembic upgrade
                # head`` build the schema from scratch.
                print("[pre-migration-repair] no alembic_version table; preflight not required")
                return
            cur.execute("SELECT version_num FROM alembic_version")
            versions = {row[0] for row in cur.fetchall()}
            if _PRE_RESET_REVISION not in versions:
                print("[pre-migration-repair] project reset preflight not required")
                return

            cur.execute(
                """
                SELECT p.id, p.company_id, p.code, p.name, p.status
                FROM projects p
                JOIN companies c ON c.id = p.company_id
                WHERE upper(trim(c.name)) = 'NEXORA GROUP'
                  AND (
                    (trim(p.code) = '21000' AND p.name = 'Cerco Perimetral')
                    OR
                    (trim(p.code) = '22000' AND p.name = 'Portones y Verjas')
                  )
                ORDER BY p.code
                FOR UPDATE
                """
            )
            projects = cur.fetchall()
            if not projects:
                print("[pre-migration-repair] target projects already absent")
                return

            target_ids = [row[0] for row in projects]
            cur.execute(
                """
                SELECT
                    tc.table_schema,
                    tc.table_name,
                    kcu.column_name,
                    cols.is_nullable,
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
                JOIN information_schema.columns cols
                  ON cols.table_schema = tc.table_schema
                 AND cols.table_name = tc.table_name
                 AND cols.column_name = kcu.column_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND ccu.table_name = 'projects'
                  AND ccu.table_schema = 'public'
                  AND rc.delete_rule IN ('NO ACTION', 'RESTRICT')
                ORDER BY tc.table_schema, tc.table_name, kcu.column_name
                """
            )
            references = cur.fetchall()

            nullable_refs: list[tuple[str, str, str, int, bool]] = []
            mandatory_refs: list[tuple[str, str, str, int]] = []
            for schema, table, column, is_nullable, _delete_rule in references:
                count_query = sql.SQL("SELECT count(*) FROM {}.{} WHERE {} = ANY(%s)").format(
                    sql.Identifier(schema),
                    sql.Identifier(table),
                    sql.Identifier(column),
                )
                cur.execute(count_query, (target_ids,))
                count = int(cur.fetchone()[0])
                if count == 0:
                    continue
                item = (schema, table, column, count)
                if is_nullable == "YES":
                    cur.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_schema = %s
                              AND table_name = %s
                              AND column_name = 'scope'
                        )
                        """,
                        (schema, table),
                    )
                    nullable_refs.append((*item, bool(cur.fetchone()[0])))
                else:
                    mandatory_refs.append(item)

            if mandatory_refs:
                details = ", ".join(
                    f"{schema}.{table}.{column}={count}"
                    for schema, table, column, count in mandatory_refs
                )
                raise RuntimeError(
                    "Authorized project reset remains blocked by mandatory references: " + details
                )

            detached_counts: dict[str, int] = defaultdict(int)
            for schema, table, column, _count, has_scope in nullable_refs:
                if has_scope:
                    # A nullable project_id can still be coupled to an
                    # operation-scope CHECK. Preserve the business record as
                    # company-general history instead of violating the CHECK
                    # while detaching the deleted project.
                    update_query = sql.SQL(
                        "UPDATE {}.{} SET {} = NULL, {} = 'GENERAL' WHERE {} = ANY(%s)"
                    ).format(
                        sql.Identifier(schema),
                        sql.Identifier(table),
                        sql.Identifier(column),
                        sql.Identifier("scope"),
                        sql.Identifier(column),
                    )
                else:
                    update_query = sql.SQL(
                        "UPDATE {}.{} SET {} = NULL WHERE {} = ANY(%s)"
                    ).format(
                        sql.Identifier(schema),
                        sql.Identifier(table),
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                cur.execute(update_query, (target_ids,))
                detached_counts[f"{schema}.{table}.{column}"] += cur.rowcount

            # Preserve an explicit audit trail that survives project deletion.
            detached_snapshot = dict(sorted(detached_counts.items()))
            for project_id, company_id, code, name, status in projects:
                cur.execute(
                    """
                    INSERT INTO audit_logs (
                        id, actor_user_id, action, entity_type, entity_id,
                        company_id, project_id, before, after, correlation_id
                    ) VALUES (
                        %s, NULL, 'project.reset.authorized', 'project', %s,
                        %s, NULL, %s::jsonb, %s::jsonb, %s
                    )
                    """,
                    (
                        uuid.uuid4(),
                        project_id,
                        company_id,
                        json.dumps({"code": code, "name": name, "status": status}),
                        json.dumps(
                            {
                                "deletedByAuthorizedReset": True,
                                "detachedNullableReferences": detached_snapshot,
                            }
                        ),
                        _CORRELATION_ID,
                    ),
                )

        conn.commit()

    if nullable_refs:
        summary = ", ".join(
            f"{schema}.{table}.{column}={count}"
            for schema, table, column, count, _has_scope in nullable_refs
        )
        print(f"[pre-migration-repair] detached nullable references: {summary}")
    print(f"[pre-migration-repair] authorized target projects prepared: {len(projects)}")


if __name__ == "__main__":
    run_authorized_project_reset_preflight()
