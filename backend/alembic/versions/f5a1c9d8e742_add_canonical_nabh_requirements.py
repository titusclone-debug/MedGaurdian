"""add canonical NABH requirements and knowledge governance

Revision ID: f5a1c9d8e742
Revises: e41b29f24c7a
Create Date: 2026-06-23

This is an additive compatibility migration. Existing synthetic measurable
element IDs are mirrored into the canonical requirement table so deployed
hospital state remains addressable while the official corpus is reviewed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f5a1c9d8e742"
down_revision: Union[str, None] = "e41b29f24c7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


classification_enum = postgresql.ENUM(
    "CORE",
    "COMMITMENT",
    "ACHIEVEMENT",
    "EXCELLENCE",
    name="nabhrequirementclassification",
    create_type=False,
)
authority_enum = postgresql.ENUM(
    "NORMATIVE",
    "OFFICIAL_INTERPRETATION",
    "MEDGUARDIAN_INTERPRETATION",
    "IMPLEMENTATION_GUIDANCE",
    name="knowledgeauthoritylevel",
    create_type=False,
)
publication_enum = postgresql.ENUM(
    "DISCOVERED",
    "EXTRACTED",
    "UNDER_REVIEW",
    "VERIFIED",
    "APPROVED",
    "PUBLISHED",
    "SUPERSEDED",
    "RETIRED",
    "REJECTED",
    name="knowledgepublicationstatus",
    create_type=False,
)
rights_enum = postgresql.ENUM(
    "UNKNOWN",
    "REFERENCE_ONLY",
    "RESTRICTED_INTERNAL",
    "EXTRACT_ONLY",
    "FULL_TEXT_PERMITTED",
    "PERMISSION_REQUIRED",
    name="sourcerightsstatus",
    create_type=False,
)
applicability_enum = postgresql.ENUM(
    "APPLICABLE",
    "CONDITIONAL",
    "NOT_APPLICABLE",
    "MANUAL_REVIEW",
    name="applicabilitydefault",
    create_type=False,
)


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_enum_if_missing(connection, enum_name: str, values: tuple[str, ...]) -> None:
    labels = ", ".join(f"'{value}'" for value in values)
    connection.execute(sa.text(f"""
        DO $$
        BEGIN
            CREATE TYPE {enum_name} AS ENUM ({labels});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """))


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        _create_enum_if_missing(
            connection,
            "nabhrequirementclassification",
            ("CORE", "COMMITMENT", "ACHIEVEMENT", "EXCELLENCE"),
        )
        _create_enum_if_missing(
            connection,
            "knowledgeauthoritylevel",
            (
                "NORMATIVE",
                "OFFICIAL_INTERPRETATION",
                "MEDGUARDIAN_INTERPRETATION",
                "IMPLEMENTATION_GUIDANCE",
            ),
        )
        _create_enum_if_missing(
            connection,
            "knowledgepublicationstatus",
            (
                "DISCOVERED",
                "EXTRACTED",
                "UNDER_REVIEW",
                "VERIFIED",
                "APPROVED",
                "PUBLISHED",
                "SUPERSEDED",
                "RETIRED",
                "REJECTED",
            ),
        )
        _create_enum_if_missing(
            connection,
            "sourcerightsstatus",
            (
                "UNKNOWN",
                "REFERENCE_ONLY",
                "RESTRICTED_INTERNAL",
                "EXTRACT_ONLY",
                "FULL_TEXT_PERMITTED",
                "PERMISSION_REQUIRED",
            ),
        )
        _create_enum_if_missing(
            connection,
            "applicabilitydefault",
            ("APPLICABLE", "CONDITIONAL", "NOT_APPLICABLE", "MANUAL_REVIEW"),
        )

    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "nabh_requirements" not in table_names:
        op.create_table(
            "nabh_requirements",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("edition_id", sa.String(), nullable=False),
            sa.Column("standard_id", sa.String(), nullable=False),
            sa.Column("official_code", sa.String(length=100), nullable=False),
            sa.Column("canonical_code", sa.String(length=100), nullable=False),
            sa.Column("official_text", sa.Text(), nullable=True),
            sa.Column("display_text", sa.Text(), nullable=False),
            sa.Column("classification", classification_enum, nullable=True),
            sa.Column("documentation_required", sa.Boolean(), nullable=True),
            sa.Column("applicability_default", applicability_enum, nullable=False),
            sa.Column("scoring_weight", sa.Float(), nullable=False),
            sa.Column("risk_weight", sa.Float(), nullable=False),
            sa.Column("default_owner_role", sa.String(length=100), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False),
            sa.Column("authority_level", authority_enum, nullable=False),
            sa.Column("publication_status", publication_enum, nullable=False),
            sa.Column("source_status", sa.String(length=50), nullable=False),
            sa.Column("effective_from", sa.DateTime(), nullable=True),
            sa.Column("effective_to", sa.DateTime(), nullable=True),
            sa.Column("verified_by", sa.String(), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("change_reason", sa.Text(), nullable=True),
            sa.Column("legacy_measurable_element_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("retired_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["approved_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["edition_id"], ["nabh_editions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["legacy_measurable_element_id"],
                ["nabh_measurable_elements.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(["standard_id"], ["nabh_standards.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["verified_by"], ["staff.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "edition_id",
                "canonical_code",
                name="uq_nabh_requirement_edition_code",
            ),
            sa.UniqueConstraint(
                "legacy_measurable_element_id",
                name="uq_nabh_requirement_legacy_meas",
            ),
        )
        op.create_index("idx_nabh_requirement_edition", "nabh_requirements", ["edition_id"])
        op.create_index("idx_nabh_requirement_standard", "nabh_requirements", ["standard_id"])
        op.create_index(
            "idx_nabh_requirement_classification",
            "nabh_requirements",
            ["classification"],
        )
        op.create_index(
            "idx_nabh_requirement_publication",
            "nabh_requirements",
            ["publication_status"],
        )

    source_columns = [
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("pdf_page_count", sa.Integer(), nullable=True),
        sa.Column("printed_page_start", sa.Integer(), nullable=True),
        sa.Column("printed_page_end", sa.Integer(), nullable=True),
        sa.Column("isbn", sa.String(length=50), nullable=True),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("programme", sa.String(length=100), nullable=True),
        sa.Column("acquisition_method", sa.String(length=100), nullable=True),
        sa.Column("acquired_at", sa.DateTime(), nullable=True),
        sa.Column(
            "authority_level",
            authority_enum,
            nullable=False,
            server_default="NORMATIVE",
        ),
        sa.Column(
            "rights_status",
            rights_enum,
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("rights_note", sa.Text(), nullable=True),
        sa.Column(
            "may_store_full_text",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "may_display_full_text",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "may_create_embeddings",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "verification_status",
            publication_enum,
            nullable=False,
            server_default="DISCOVERED",
        ),
        sa.Column("verified_by", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("superseded_by_document_id", sa.String(), nullable=True),
    ]
    for column in source_columns:
        _add_column_if_missing("nabh_source_documents", column)
    with op.batch_alter_table("nabh_source_documents") as batch_op:
        batch_op.create_foreign_key(
            "fk_nabh_source_superseded_by",
            "nabh_source_documents",
            ["superseded_by_document_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_nabh_source_verified_by",
            "staff",
            ["verified_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_nabh_source_approved_by",
            "staff",
            ["approved_by"],
            ["id"],
            ondelete="SET NULL",
        )

    _add_column_if_missing(
        "nabh_chapters",
        sa.Column("official_requirements_count", sa.Integer(), nullable=True),
    )

    if "nabh_source_anomalies" not in table_names:
        op.create_table(
            "nabh_source_anomalies",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=False),
            sa.Column("anomaly_code", sa.String(length=100), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("source_locator", sa.String(length=255), nullable=False),
            sa.Column("observed_value", sa.Text(), nullable=True),
            sa.Column("reconciled_value", sa.Text(), nullable=True),
            sa.Column("reconciliation_basis", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("verified_by", sa.String(), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["document_id"], ["nabh_source_documents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["verified_by"], ["staff.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "document_id",
                "anomaly_code",
                name="uq_nabh_source_anomaly",
            ),
        )
        op.create_index(
            "idx_nabh_source_anomaly_document",
            "nabh_source_anomalies",
            ["document_id"],
        )
        op.create_index(
            "idx_nabh_source_anomaly_status",
            "nabh_source_anomalies",
            ["status"],
        )

    if "nabh_knowledge_changes" not in table_names:
        op.create_table(
            "nabh_knowledge_changes",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("edition_id", sa.String(), nullable=False),
            sa.Column("change_code", sa.String(length=100), nullable=False),
            sa.Column("what_changed", sa.Text(), nullable=False),
            sa.Column("why_changed", sa.Text(), nullable=False),
            sa.Column("supporting_source_ids", sa.JSON(), nullable=False),
            sa.Column("impacted_requirement_ids", sa.JSON(), nullable=False),
            sa.Column("hospitals_requiring_recompute", sa.JSON(), nullable=False),
            sa.Column("hospitals_requiring_notification", sa.JSON(), nullable=False),
            sa.Column("proposed_by", sa.String(), nullable=True),
            sa.Column("reviewed_by", sa.String(), nullable=True),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("published_by", sa.String(), nullable=True),
            sa.Column("status", publication_enum, nullable=False),
            sa.Column("effective_date", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["approved_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["edition_id"], ["nabh_editions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["proposed_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["published_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["reviewed_by"], ["staff.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("change_code"),
        )
        op.create_index(
            "idx_nabh_knowledge_change_edition",
            "nabh_knowledge_changes",
            ["edition_id"],
        )
        op.create_index(
            "idx_nabh_knowledge_change_status",
            "nabh_knowledge_changes",
            ["status"],
        )

    if "nabh_knowledge_content" not in table_names:
        op.create_table(
            "nabh_knowledge_content",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("edition_id", sa.String(), nullable=False),
            sa.Column("requirement_id", sa.String(), nullable=True),
            sa.Column("hospital_id", sa.String(), nullable=True),
            sa.Column("source_document_id", sa.String(), nullable=True),
            sa.Column("citation_id", sa.String(), nullable=True),
            sa.Column("content_type", sa.String(length=100), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("content_checksum", sa.String(length=64), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("authority_level", authority_enum, nullable=False),
            sa.Column("publication_status", publication_enum, nullable=False),
            sa.Column("change_reason", sa.Text(), nullable=False),
            sa.Column("supersedes_content_id", sa.String(), nullable=True),
            sa.Column("proposed_by", sa.String(), nullable=True),
            sa.Column("reviewed_by", sa.String(), nullable=True),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("published_by", sa.String(), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("effective_from", sa.DateTime(), nullable=True),
            sa.Column("effective_to", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("retired_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["approved_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["citation_id"], ["nabh_requirement_citations.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["edition_id"], ["nabh_editions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["proposed_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["published_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["requirement_id"], ["nabh_requirements.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by"], ["staff.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_document_id"], ["nabh_source_documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["supersedes_content_id"], ["nabh_knowledge_content.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(
                "authority_level <> 'NORMATIVE'",
                name="ck_nabh_knowledge_content_not_normative",
            ),
        )
        op.create_index(
            "idx_nabh_knowledge_content_edition",
            "nabh_knowledge_content",
            ["edition_id"],
        )
        op.create_index(
            "idx_nabh_knowledge_content_requirement",
            "nabh_knowledge_content",
            ["requirement_id"],
        )
        op.create_index(
            "idx_nabh_knowledge_content_hospital",
            "nabh_knowledge_content",
            ["hospital_id"],
        )
        op.create_index(
            "idx_nabh_knowledge_content_status",
            "nabh_knowledge_content",
            ["publication_status"],
        )
        op.create_index(
            "idx_nabh_knowledge_content_authority",
            "nabh_knowledge_content",
            ["authority_level"],
        )

    dependent_columns = {
        "nabh_evidence_requirements": "requirement_id",
        "nabh_requirement_citations": "requirement_id",
        "nabh_applicability_rules": "requirement_id",
        "hospital_nabh_requirements": "canonical_requirement_id",
        "nabh_legacy_migration_maps": "canonical_requirement_id",
    }
    for table_name, column_name in dependent_columns.items():
        if column_name not in _columns(table_name):
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.add_column(sa.Column(column_name, sa.String(), nullable=True))
                batch_op.create_foreign_key(
                    f"fk_{table_name}_{column_name}_nabh_requirements",
                    "nabh_requirements",
                    [column_name],
                    ["id"],
                    ondelete="CASCADE",
                )

    citation_columns = [
        sa.Column("printed_page_number", sa.String(length=50), nullable=True),
        sa.Column("pdf_page_index", sa.Integer(), nullable=True),
        sa.Column("source_heading", sa.String(length=255), nullable=True),
        sa.Column("passage_checksum", sa.String(length=64), nullable=True),
        sa.Column("extraction_method", sa.String(length=100), nullable=True),
        sa.Column(
            "human_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("verified_by", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
    ]
    for column in citation_columns:
        _add_column_if_missing("nabh_requirement_citations", column)

    nullable_legacy_columns = (
        ("nabh_evidence_requirements", "measurable_element_id"),
        ("nabh_requirement_citations", "measurable_element_id"),
        ("nabh_applicability_rules", "measurable_element_id"),
        ("hospital_nabh_requirements", "requirement_id"),
    )
    for table_name, column_name in nullable_legacy_columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=sa.String(),
                nullable=True,
            )

    with op.batch_alter_table("nabh_requirement_citations") as batch_op:
        batch_op.create_foreign_key(
            "fk_nabh_citation_verified_by",
            "staff",
            ["verified_by"],
            ["id"],
            ondelete="SET NULL",
        )

    connection.execute(sa.text("""
        UPDATE nabh_chapters
        SET official_requirements_count = official_measurable_elements_count
        WHERE official_requirements_count IS NULL
    """))
    connection.execute(sa.text("""
        INSERT INTO nabh_requirements (
            id, edition_id, standard_id, official_code, canonical_code,
            official_text, display_text, classification, documentation_required,
            applicability_default, scoring_weight, risk_weight, default_owner_role,
            display_order, authority_level, publication_status, source_status,
            effective_from, change_reason, legacy_measurable_element_id
        )
        SELECT
            me.id, me.edition_id, oe.standard_id, me.canonical_code,
            me.canonical_code, NULL, me.description, NULL, NULL,
            me.applicability_default, me.scoring_weight, me.risk_weight,
            me.default_owner_role, me.display_order,
            'MEDGUARDIAN_INTERPRETATION', 'PUBLISHED',
            'legacy_synthetic', ed.effective_date,
            'Compatibility mirror created during Phase 1.5 schema adoption.',
            me.id
        FROM nabh_measurable_elements me
        JOIN nabh_objective_elements oe ON oe.id = me.objective_element_id
        JOIN nabh_editions ed ON ed.id = me.edition_id
        WHERE NOT EXISTS (
            SELECT 1 FROM nabh_requirements req WHERE req.id = me.id
        )
    """))
    connection.execute(sa.text("""
        UPDATE nabh_evidence_requirements
        SET requirement_id = measurable_element_id
        WHERE requirement_id IS NULL AND measurable_element_id IS NOT NULL
    """))
    connection.execute(sa.text("""
        UPDATE nabh_requirement_citations
        SET requirement_id = measurable_element_id
        WHERE requirement_id IS NULL AND measurable_element_id IS NOT NULL
    """))
    connection.execute(sa.text("""
        UPDATE nabh_applicability_rules
        SET requirement_id = measurable_element_id
        WHERE requirement_id IS NULL AND measurable_element_id IS NOT NULL
    """))
    connection.execute(sa.text("""
        UPDATE hospital_nabh_requirements
        SET canonical_requirement_id = requirement_id
        WHERE canonical_requirement_id IS NULL AND requirement_id IS NOT NULL
    """))
    connection.execute(sa.text("""
        UPDATE nabh_legacy_migration_maps
        SET canonical_requirement_id = new_requirement_id
        WHERE canonical_requirement_id IS NULL AND new_requirement_id IS NOT NULL
    """))

    for table_name, constraint_name, condition in (
        (
            "nabh_evidence_requirements",
            "ck_evidence_requirement_parent",
            "measurable_element_id IS NOT NULL OR requirement_id IS NOT NULL",
        ),
        (
            "nabh_requirement_citations",
            "ck_requirement_citation_parent",
            "measurable_element_id IS NOT NULL OR requirement_id IS NOT NULL",
        ),
        (
            "nabh_applicability_rules",
            "ck_applicability_rule_parent",
            "measurable_element_id IS NOT NULL OR requirement_id IS NOT NULL",
        ),
        (
            "hospital_nabh_requirements",
            "ck_hospital_requirement_parent",
            "requirement_id IS NOT NULL OR canonical_requirement_id IS NOT NULL",
        ),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_check_constraint(constraint_name, condition)
    connection.execute(sa.text("""
        INSERT INTO nabh_source_documents (
            id, edition_id, title, publisher, edition_version,
            file_path_or_url, checksum, file_size_bytes, pdf_page_count,
            printed_page_start, printed_page_end, isbn, document_type,
            programme, acquisition_method, authority_level, rights_status,
            rights_note, may_store_full_text, may_display_full_text,
            may_create_embeddings, verification_status, effective_date
        )
        SELECT
            'nabh-source-6-standard', ed.id,
            'NABH Accreditation Standards for Hospitals',
            'National Accreditation Board for Hospitals and Healthcare Providers',
            '6th Edition', NULL,
            '0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A',
            16404482, 242, 1, 230, '978-81-965264-9-8',
            'accreditation_standard', 'Hospitals Accreditation Programme',
            'operator_provided_protected_copy', 'NORMATIVE',
            'PERMISSION_REQUIRED',
            'All rights reserved; reproduction or transmission requires written permission.',
            false, false, false, 'VERIFIED', '2025-01-01'
        FROM nabh_editions ed
        WHERE ed.version = '6.0'
          AND NOT EXISTS (
              SELECT 1 FROM nabh_source_documents doc
              WHERE doc.edition_id = ed.id
                AND doc.checksum =
                '0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A'
          )
    """))
    source_anomalies = (
        (
            "nabh-anomaly-cop-summary",
            "COP-SUMMARY-TOTAL",
            "COP summary total",
            "The source summary lists 135 COP Objective Elements.",
            "printed page 19",
            "COP objective elements = 135",
            "COP objective elements = 136",
            "The detailed COP enumeration and 13 + 107 + 12 + 4 classification total establish 136.",
        ),
        (
            "nabh-anomaly-hrm-contents",
            "CONTENTS-HRM-START",
            "HRM contents start page",
            "The contents page lists the HRM chapter start as 159.",
            "contents page",
            "HRM starts at printed page 159",
            "HRM starts at printed page 150",
            "The HRM chapter title and summary begin at printed page 150.",
        ),
        (
            "nabh-anomaly-ims-contents",
            "CONTENTS-IMS-START",
            "IMS contents start page",
            "The contents page lists the IMS chapter start as 186.",
            "contents page",
            "IMS starts at printed page 186",
            "IMS starts at printed page 166",
            "The IMS chapter title and summary begin at printed page 166.",
        ),
    )
    for (
        anomaly_id,
        anomaly_code,
        title,
        description,
        locator,
        observed,
        reconciled,
        basis,
    ) in source_anomalies:
        connection.execute(sa.text("""
            INSERT INTO nabh_source_anomalies (
                id, document_id, anomaly_code, title, description,
                source_locator, observed_value, reconciled_value,
                reconciliation_basis, status
            )
            SELECT
                :id, doc.id, :code, :title, :description, :locator,
                :observed, :reconciled, :basis, 'reconciled'
            FROM nabh_source_documents doc
            WHERE doc.checksum =
                '0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A'
              AND doc.id = (
                  SELECT MIN(source_doc.id)
                  FROM nabh_source_documents source_doc
                  WHERE source_doc.checksum =
                    '0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A'
              )
              AND NOT EXISTS (
                  SELECT 1 FROM nabh_source_anomalies anomaly
                  WHERE anomaly.document_id = doc.id
                    AND anomaly.anomaly_code = :code
              )
        """), {
            "id": anomaly_id,
            "code": anomaly_code,
            "title": title,
            "description": description,
            "locator": locator,
            "observed": observed,
            "reconciled": reconciled,
            "basis": basis,
        })

    op.create_index(
        "idx_evidence_req_requirement",
        "nabh_evidence_requirements",
        ["requirement_id"],
    )
    with op.batch_alter_table("nabh_evidence_requirements") as batch_op:
        batch_op.create_unique_constraint(
            "uq_evidence_req_requirement_code",
            ["requirement_id", "evidence_code"],
        )
    op.create_index(
        "idx_citation_requirement",
        "nabh_requirement_citations",
        ["requirement_id"],
    )
    op.create_index(
        "idx_app_rule_requirement",
        "nabh_applicability_rules",
        ["requirement_id"],
    )
    op.create_index(
        "idx_hosp_req_canonical_requirement",
        "hospital_nabh_requirements",
        ["canonical_requirement_id"],
    )
    with op.batch_alter_table("hospital_nabh_requirements") as batch_op:
        batch_op.create_unique_constraint(
            "uq_hospital_canonical_requirement",
            ["hospital_id", "canonical_requirement_id"],
        )
    op.create_index(
        "idx_legacy_migration_canonical_requirement",
        "nabh_legacy_migration_maps",
        ["canonical_requirement_id"],
    )


def downgrade() -> None:
    for table_name, constraint_name in (
        ("hospital_nabh_requirements", "ck_hospital_requirement_parent"),
        ("nabh_applicability_rules", "ck_applicability_rule_parent"),
        ("nabh_requirement_citations", "ck_requirement_citation_parent"),
        ("nabh_evidence_requirements", "ck_evidence_requirement_parent"),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(constraint_name, type_="check")

    op.drop_index(
        "idx_legacy_migration_canonical_requirement",
        table_name="nabh_legacy_migration_maps",
    )
    with op.batch_alter_table("hospital_nabh_requirements") as batch_op:
        batch_op.drop_constraint(
            "uq_hospital_canonical_requirement",
            type_="unique",
        )
    op.drop_index(
        "idx_hosp_req_canonical_requirement",
        table_name="hospital_nabh_requirements",
    )
    op.drop_index("idx_app_rule_requirement", table_name="nabh_applicability_rules")
    op.drop_index("idx_citation_requirement", table_name="nabh_requirement_citations")
    with op.batch_alter_table("nabh_evidence_requirements") as batch_op:
        batch_op.drop_constraint(
            "uq_evidence_req_requirement_code",
            type_="unique",
        )
    op.drop_index("idx_evidence_req_requirement", table_name="nabh_evidence_requirements")

    with op.batch_alter_table("nabh_requirement_citations") as batch_op:
        batch_op.drop_constraint(
            "fk_nabh_citation_verified_by",
            type_="foreignkey",
        )

    for table_name, column_name in (
        ("nabh_legacy_migration_maps", "canonical_requirement_id"),
        ("hospital_nabh_requirements", "canonical_requirement_id"),
        ("nabh_applicability_rules", "requirement_id"),
        ("nabh_requirement_citations", "requirement_id"),
        ("nabh_evidence_requirements", "requirement_id"),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column(column_name)

    with op.batch_alter_table("nabh_requirement_citations") as batch_op:
        for column_name in (
            "verified_at",
            "verified_by",
            "human_verified",
            "extraction_method",
            "passage_checksum",
            "source_heading",
            "pdf_page_index",
            "printed_page_number",
        ):
            batch_op.drop_column(column_name)

    for table_name, column_name in (
        ("nabh_evidence_requirements", "measurable_element_id"),
        ("nabh_requirement_citations", "measurable_element_id"),
        ("nabh_applicability_rules", "measurable_element_id"),
        ("hospital_nabh_requirements", "requirement_id"),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=sa.String(),
                nullable=False,
            )

    op.drop_table("nabh_knowledge_content")
    op.drop_table("nabh_knowledge_changes")
    op.drop_table("nabh_source_anomalies")
    with op.batch_alter_table("nabh_chapters") as batch_op:
        batch_op.drop_column("official_requirements_count")
    with op.batch_alter_table("nabh_source_documents") as batch_op:
        batch_op.drop_constraint(
            "fk_nabh_source_approved_by",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_nabh_source_verified_by",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_nabh_source_superseded_by",
            type_="foreignkey",
        )
    with op.batch_alter_table("nabh_source_documents") as batch_op:
        for column_name in (
            "superseded_by_document_id",
            "approved_at",
            "approved_by",
            "verified_at",
            "verified_by",
            "verification_status",
            "may_create_embeddings",
            "may_display_full_text",
            "may_store_full_text",
            "rights_note",
            "rights_status",
            "authority_level",
            "acquired_at",
            "acquisition_method",
            "programme",
            "document_type",
            "isbn",
            "printed_page_end",
            "printed_page_start",
            "pdf_page_count",
            "file_size_bytes",
        ):
            batch_op.drop_column(column_name)
    op.drop_table("nabh_requirements")

    bind = op.get_bind()
    for enum_type in (
        classification_enum,
        authority_enum,
        publication_enum,
        rights_enum,
    ):
        enum_type.drop(bind, checkfirst=True)
