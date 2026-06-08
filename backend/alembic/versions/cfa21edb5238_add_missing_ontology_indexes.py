"""add_missing_ontology_indexes

Revision ID: cfa21edb5238
Revises: b6e15beae6ec
Create Date: 2026-06-08 15:18:35.262426

CRITICAL: Although this migration file is named after "add_missing_ontology_indexes", it
repairs ALL schema drift in the active development database ('medguardian.db') relative
to the consolidated baseline migration ('7ec208e12d9f').
Specifically, it:
1. Adds missing nullable 'retired_at' columns on ontology tables (which were defined
   in the baseline models/migrations but omitted in the dev DB due to manual stamping).
2. Adds missing explicit indexes.

All operations are guarded dynamically using SQL reflection to ensure safe, idempotent
execution on both fresh databases and existing databases with schema drift.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cfa21edb5238'
down_revision: Union[str, None] = 'b6e15beae6ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def index_exists(conn, table_name, index_name) -> bool:
    """Helper to dynamically inspect if an index exists to prevent duplicate index errors."""
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def column_exists(conn, table_name, column_name) -> bool:
    """Helper to dynamically inspect if a column exists to prevent duplicate column errors."""
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add missing retired_at columns defensively to repair baseline schema drift
    # Note: These columns are nullable and aligned with baseline models to ensure no impact on existing queries.
    if not column_exists(conn, 'nabh_applicability_rules', 'retired_at'):
        op.add_column('nabh_applicability_rules', sa.Column('retired_at', sa.DateTime(), nullable=True))
    if not column_exists(conn, 'nabh_evidence_requirements', 'retired_at'):
        op.add_column('nabh_evidence_requirements', sa.Column('retired_at', sa.DateTime(), nullable=True))
    if not column_exists(conn, 'nabh_requirement_citations', 'retired_at'):
        op.add_column('nabh_requirement_citations', sa.Column('retired_at', sa.DateTime(), nullable=True))
    if not column_exists(conn, 'nabh_source_documents', 'retired_at'):
        op.add_column('nabh_source_documents', sa.Column('retired_at', sa.DateTime(), nullable=True))

    # 2. Add missing explicit indexes defensively
    if not index_exists(conn, 'nabh_applicability_rules', 'idx_app_rule_meas_el'):
        op.create_index('idx_app_rule_meas_el', 'nabh_applicability_rules', ['measurable_element_id'], unique=False)

    if not index_exists(conn, 'nabh_chapters', 'idx_chapter_edition'):
        op.create_index('idx_chapter_edition', 'nabh_chapters', ['edition_id'], unique=False)

    if not index_exists(conn, 'nabh_evidence_requirements', 'idx_evidence_req_meas_el'):
        op.create_index('idx_evidence_req_meas_el', 'nabh_evidence_requirements', ['measurable_element_id'], unique=False)

    if not index_exists(conn, 'nabh_measurable_elements', 'idx_meas_element_edition'):
        op.create_index('idx_meas_element_edition', 'nabh_measurable_elements', ['edition_id'], unique=False)

    if not index_exists(conn, 'nabh_measurable_elements', 'idx_meas_element_obj_el'):
        op.create_index('idx_meas_element_obj_el', 'nabh_measurable_elements', ['objective_element_id'], unique=False)

    if not index_exists(conn, 'nabh_objective_elements', 'idx_obj_element_edition'):
        op.create_index('idx_obj_element_edition', 'nabh_objective_elements', ['edition_id'], unique=False)

    if not index_exists(conn, 'nabh_objective_elements', 'idx_obj_element_standard'):
        op.create_index('idx_obj_element_standard', 'nabh_objective_elements', ['standard_id'], unique=False)

    if not index_exists(conn, 'nabh_requirement_citations', 'idx_citation_document'):
        op.create_index('idx_citation_document', 'nabh_requirement_citations', ['document_id'], unique=False)

    if not index_exists(conn, 'nabh_requirement_citations', 'idx_citation_meas_el'):
        op.create_index('idx_citation_meas_el', 'nabh_requirement_citations', ['measurable_element_id'], unique=False)

    if not index_exists(conn, 'nabh_source_documents', 'idx_source_doc_edition'):
        op.create_index('idx_source_doc_edition', 'nabh_source_documents', ['edition_id'], unique=False)

    if not index_exists(conn, 'nabh_standards', 'idx_standard_chapter'):
        op.create_index('idx_standard_chapter', 'nabh_standards', ['chapter_id'], unique=False)

    if not index_exists(conn, 'nabh_standards', 'idx_standard_edition'):
        op.create_index('idx_standard_edition', 'nabh_standards', ['edition_id'], unique=False)


def downgrade() -> None:
    # NOTE: These indexes and columns are baseline-level structural definitions 
    # required by the SQLAlchemy models. Downgrade is an intentional and defensive 
    # no-op. If we were to drop these indexes or columns during downgrade, we would
    # break the baseline schema on a clean installation where the baseline migration 
    # ran first. Since these corrective additions only restore the database to its 
    # designed baseline state, they are safe to leave in place indefinitely.
    pass
