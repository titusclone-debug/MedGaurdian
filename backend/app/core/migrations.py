"""Alembic migration-state inspection for startup and release checks."""
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Engine


def inspect_migration_state(engine: Engine) -> dict:
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    expected_heads = set(scripts.get_heads())

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_heads = set(context.get_current_heads())

    return {
        "is_current": current_heads == expected_heads,
        "current_heads": sorted(current_heads),
        "expected_heads": sorted(expected_heads),
        "unapplied_heads": sorted(expected_heads - current_heads),
        "unexpected_heads": sorted(current_heads - expected_heads),
    }
