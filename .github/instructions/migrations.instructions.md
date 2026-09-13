---
applyTo: "backend/alembic/**/*.py,backend/app/models/**/*.py"
---

# Database Migration Rules

Every migration must be tested against a fresh PostgreSQL database.

Reject:

- accidental DROP TABLE;
- accidental DROP COLUMN;
- destructive raw DROP SQL;
- NOT NULL additions without safe backfill where existing rows can exist;
- broken foreign keys;
- migration graph with multiple heads;
- model/schema drift without a migration.

Destructive migration operations require an explicit inline marker:

`NEXORA_ALLOW_DESTRUCTIVE_MIGRATION`

and must be justified in the pull request.
