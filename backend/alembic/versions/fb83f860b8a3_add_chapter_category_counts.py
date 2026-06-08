"""add_chapter_category_counts

Revision ID: fb83f860b8a3
Revises: ba0e08903243
Create Date: 2026-06-08 23:55:55.634200
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = 'fb83f860b8a3'
down_revision: Union[str, None] = 'ba0e08903243'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(conn, table_name, column_name) -> bool:
    """Helper to dynamically inspect if a column exists to prevent duplicate column errors."""
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()
    
    if not column_exists(conn, 'nabh_chapters', 'core_count'):
        op.add_column('nabh_chapters', sa.Column('core_count', sa.Integer(), nullable=True))
    if not column_exists(conn, 'nabh_chapters', 'commitment_count'):
        op.add_column('nabh_chapters', sa.Column('commitment_count', sa.Integer(), nullable=True))
    if not column_exists(conn, 'nabh_chapters', 'achievement_count'):
        op.add_column('nabh_chapters', sa.Column('achievement_count', sa.Integer(), nullable=True))
    if not column_exists(conn, 'nabh_chapters', 'excellence_count'):
        op.add_column('nabh_chapters', sa.Column('excellence_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    pass
