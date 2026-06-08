import os
import sqlite3
import subprocess
import sys

def run_clean_migration_test():
    """Verify that a fresh SQLite file database can migrate from baseline to head without conflicts."""
    db_file = "temp_mig_test.db"
    
    # Pre-clean any existing DB file and SQLite sidecar files
    for suffix in ["", "-journal", "-wal", "-shm"]:
        path = db_file + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        
    print("Testing clean migration path from scratch on physical temp database...")
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///./{db_file}"
    
    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=".",
            env=env
        )
        
        if result.returncode != 0:
            print("FAIL: Clean migration path failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
        print("SUCCESS: Clean migration path verified successfully (no conflicts).")
        return True
    finally:
        # Guarantee cleanup of temp database and sidecar files
        for suffix in ["", "-journal", "-wal", "-shm"]:
            path = db_file + suffix
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

def audit_dev_db_indexes():
    """Verify that all 12 explicit indexes exist in the dev database."""
    db_file = "medguardian.db"
    if not os.path.exists(db_file):
        print(f"FAIL: Dev database {db_file} not found!")
        return False
        
    print(f"Auditing explicit indexes in {db_file}...")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    active_indexes = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    required_indexes = [
        "idx_app_rule_meas_el",
        "idx_chapter_edition",
        "idx_evidence_req_meas_el",
        "idx_meas_element_edition",
        "idx_meas_element_obj_el",
        "idx_obj_element_edition",
        "idx_obj_element_standard",
        "idx_citation_document",
        "idx_citation_meas_el",
        "idx_source_doc_edition",
        "idx_standard_chapter",
        "idx_standard_edition"
    ]
    
    missing = []
    for idx in required_indexes:
        if idx not in active_indexes:
            missing.append(idx)
            
    if missing:
        print(f"FAIL: The following {len(missing)} indexes are missing in the dev DB:")
        for idx in missing:
            print(f"  - {idx}")
        return False
        
    print("SUCCESS: All 12 required ontology indexes exist in the dev DB.")
    return True

def main():
    success_mig = run_clean_migration_test()
    print("=" * 60)
    success_audit = audit_dev_db_indexes()
    print("=" * 60)
    
    if not (success_mig and success_audit):
        print("Task 6 Verification FAILED.")
        sys.exit(1)
    else:
        print("Task 6 Verification PASSED successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
