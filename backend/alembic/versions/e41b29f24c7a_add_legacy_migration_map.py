"""add legacy migration provenance map

Revision ID: e41b29f24c7a
Revises: dd9268c5febf
Create Date: 2026-06-23

The live PostgreSQL database may already contain this table because earlier
startup code used Base.metadata.create_all. The migration therefore checks for
the table before creating it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e41b29f24c7a"
down_revision: Union[str, None] = "dd9268c5febf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "nabh_legacy_migration_maps" in inspector.get_table_names():
        return

    op.create_table(
        "nabh_legacy_migration_maps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("hospital_id", sa.String(), nullable=False),
        sa.Column("legacy_objective_id", sa.String(), nullable=False),
        sa.Column("legacy_standard_code", sa.String(length=100), nullable=False),
        sa.Column("new_requirement_id", sa.String(), nullable=True),
        sa.Column("mapping_level", sa.String(length=50), nullable=False),
        sa.Column("mapping_status", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("migrated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["legacy_objective_id"], ["nabh_objectives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["new_requirement_id"], ["nabh_measurable_elements.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "legacy_objective_id",
            "new_requirement_id",
            "mapping_level",
            name="uq_legacy_migration_target",
        ),
    )
    op.create_index(
        "idx_legacy_migration_hospital",
        "nabh_legacy_migration_maps",
        ["hospital_id"],
    )
    op.create_index(
        "idx_legacy_migration_legacy",
        "nabh_legacy_migration_maps",
        ["legacy_objective_id"],
    )
    op.create_index(
        "idx_legacy_migration_requirement",
        "nabh_legacy_migration_maps",
        ["new_requirement_id"],
    )
    op.create_index(
        "idx_legacy_migration_status",
        "nabh_legacy_migration_maps",
        ["mapping_status"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "nabh_legacy_migration_maps" not in inspector.get_table_names():
        return
    op.drop_table("nabh_legacy_migration_maps")
