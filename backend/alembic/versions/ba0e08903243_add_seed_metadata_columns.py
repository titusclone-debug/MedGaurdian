"""add_seed_metadata_columns

Revision ID: ba0e08903243
Revises: cfa21edb5238
Create Date: 2026-06-08 15:53:08.551475
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ba0e08903243'
down_revision: Union[str, None] = 'cfa21edb5238'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(conn, table_name, column_name) -> bool:
    """Helper to dynamically inspect if a column exists to prevent duplicate column errors."""
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add missing metadata columns to nabh_chapters defensively
    if not column_exists(conn, 'nabh_chapters', 'official_standards_count'):
        op.add_column('nabh_chapters', sa.Column('official_standards_count', sa.Integer(), nullable=True))
    if not column_exists(conn, 'nabh_chapters', 'official_measurable_elements_count'):
        op.add_column('nabh_chapters', sa.Column('official_measurable_elements_count', sa.Integer(), nullable=True))
    if not column_exists(conn, 'nabh_chapters', 'is_fully_seeded'):
        op.add_column('nabh_chapters', sa.Column('is_fully_seeded', sa.Boolean(), nullable=False, server_default='0'))

    # 2. Add evidence_code column and unique constraint to nabh_evidence_requirements defensively
    if not column_exists(conn, 'nabh_evidence_requirements', 'evidence_code'):
        op.add_column('nabh_evidence_requirements', sa.Column('evidence_code', sa.String(length=100), nullable=True))
        
    # Create the unique constraint on nabh_evidence_requirements using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('nabh_evidence_requirements') as batch_op:
        batch_op.create_unique_constraint('uq_evidence_req_element_code', ['measurable_element_id', 'evidence_code'])


def downgrade() -> None:
    # NOTE: Since these columns and constraints are now required by the active database 
    # models, dropping them would break model synchronization. Therefore, downgrade 
    # is a defensive no-op to prevent application crashes on schema mismatch.
    pass
