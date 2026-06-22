# Production Operations

## Current transition state

The live PostgreSQL schema was originally created with SQLAlchemy
`Base.metadata.create_all`. Application startup no longer performs production
schema creation. Alembic state is inspected and logged in warning mode while the
existing database is adopted deliberately.

Do not set `MIGRATION_CHECK_MODE=enforce` until the adoption procedure below is
complete and verified.

## One-time Alembic adoption

1. Put the service in a maintenance window.
2. Create and verify a managed PostgreSQL backup.
3. Run schema comparison against the deployed model and current Alembic head.
4. If the existing schema matches the last deployed migration, stamp that exact
   revision. Never stamp blindly.
5. Run `alembic upgrade head`.
6. Run `python scripts/check_release_readiness.py`.
7. Restart the service and run the browser acceptance gate.
8. Set `MIGRATION_CHECK_MODE=enforce`.
9. Remove `AUTO_SEED_DEMO_ON_STARTUP` and `AUTO_SEED_NABH_ON_STARTUP`.

## Release sequence

1. CI backend and frontend quality gates pass.
2. Database backup is successful.
3. Alembic upgrade runs as a release/pre-deploy operation.
4. Backend deploys.
5. `/health` and `/api/admin/nabh-health` pass.
6. Browser acceptance gate passes.
7. A service restart is performed.
8. Browser acceptance gate passes again.

## Rollback

Application rollback and database rollback are separate decisions.

- Prefer forward-fix migrations.
- Roll application code back only when the database migration is backward
  compatible with the previous application.
- Do not automatically downgrade destructive migrations.
- Restore from a verified backup only through an approved incident procedure.
- Version NABH seed releases independently from application releases and record
  the seed checksum used by each deployment.

## Backups and restore rehearsals

- Enable managed PostgreSQL backups and point-in-time recovery where available.
- Document retention with the institutional legal and privacy teams.
- Run a restore rehearsal into an isolated environment at least quarterly.
- Verify row counts, NABH seed health, audit-chain continuity, and application
  acceptance after every rehearsal.

## Vector storage

Local ChromaDB remains unsuitable as the production source of truth because its
filesystem can be ephemeral and it is not authoritative. Until a durable vector
service is selected:

- PostgreSQL and source documents remain authoritative.
- Vector data must be reproducible from those sources.
- Loss of ChromaDB must degrade semantic search, not destroy compliance state.
- Phase 2 must choose a durable managed vector store or PostgreSQL `pgvector`
  before production RAG workflows are enabled.
