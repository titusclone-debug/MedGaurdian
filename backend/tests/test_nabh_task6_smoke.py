import pytest
import sqlalchemy as sa
from sqlalchemy import text

def index_exists(conn, table_name, index_name) -> bool:
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes

def column_exists(conn, table_name, column_name) -> bool:
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def test_database_migration_indexes_smoke(db_session):
    # Enable SQLite foreign keys
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    conn = db_session.connection()

    # 1. Assert all 12 explicit indexes exist in the test database schema
    required_indexes = [
        ("nabh_applicability_rules", "idx_app_rule_meas_el"),
        ("nabh_chapters", "idx_chapter_edition"),
        ("nabh_evidence_requirements", "idx_evidence_req_meas_el"),
        ("nabh_measurable_elements", "idx_meas_element_edition"),
        ("nabh_measurable_elements", "idx_meas_element_obj_el"),
        ("nabh_objective_elements", "idx_obj_element_edition"),
        ("nabh_objective_elements", "idx_obj_element_standard"),
        ("nabh_requirement_citations", "idx_citation_document"),
        ("nabh_requirement_citations", "idx_citation_meas_el"),
        ("nabh_source_documents", "idx_source_doc_edition"),
        ("nabh_standards", "idx_standard_chapter"),
        ("nabh_standards", "idx_standard_edition")
    ]

    for table, idx_name in required_indexes:
        assert index_exists(conn, table, idx_name) is True, f"Index {idx_name} on table {table} should exist"

    # 2. Test Idempotency of dynamic checks
    # Assert that column_exists and index_exists correctly report True for pre-existing items
    assert column_exists(conn, 'nabh_chapters', 'edition_id') is True
    assert column_exists(conn, 'nabh_chapters', 'fake_col') is False
    assert index_exists(conn, 'nabh_chapters', 'fake_idx') is False

    # Simulate the migration upgrade logic on the active test database connection
    # It must complete cleanly without throwing 'Index already exists' or duplicate column exceptions.
    try:
        # Add column (already exists in models -> metadata)
        if not column_exists(conn, 'nabh_applicability_rules', 'retired_at'):
            # Should not execute this block
            assert False, "Should skip column creation"
            
        # Create index (already exists in models -> metadata)
        if not index_exists(conn, 'nabh_chapters', 'idx_chapter_edition'):
            # Should not execute this block
            assert False, "Should skip index creation"
            
    except Exception as e:
        pytest.fail(f"Idempotency checks raised unexpected error: {e}")
