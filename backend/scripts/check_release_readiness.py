"""Fail a release check when schema or NABH reference truth is not ready."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.core.migrations import inspect_migration_state
from app.nabh.seed_health import check_nabh_seed_health


def main() -> None:
    migration_state = inspect_migration_state(engine)
    db = SessionLocal()
    try:
        seed_health = check_nabh_seed_health(db)
    finally:
        db.close()

    report = {
        "migration_state": migration_state,
        "nabh_seed_health": seed_health,
    }
    print(json.dumps(report, indent=2, default=str))
    if not migration_state["is_current"] or not seed_health["is_healthy"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
