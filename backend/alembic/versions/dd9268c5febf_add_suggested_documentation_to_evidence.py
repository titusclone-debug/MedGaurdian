"""add suggested_documentation to evidence

Revision ID: dd9268c5febf
Revises: fb83f860b8a3
Create Date: 2026-06-09 19:29:49.884922
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = 'dd9268c5febf'
down_revision: Union[str, None] = 'fb83f860b8a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(conn, table_name, column_name) -> bool:
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()
    if not column_exists(conn, 'nabh_evidence_requirements', 'suggested_documentation'):
        op.add_column('nabh_evidence_requirements', sa.Column('suggested_documentation', sa.Text(), nullable=True))


def downgrade() -> None:
    pass

