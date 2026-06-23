"""Run Alembic to head under a PostgreSQL advisory transaction lock."""
import json
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import engine


MIGRATION_LOCK_ID = 604_2025_639


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))

    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": MIGRATION_LOCK_ID},
            )
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    print(json.dumps({
        "event": "database_migrations_complete",
        "database_dialect": engine.dialect.name,
        "target_revision": "head",
        "environment": os.getenv("APP_ENV", "development"),
    }))


if __name__ == "__main__":
    main()
