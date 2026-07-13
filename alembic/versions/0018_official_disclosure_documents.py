"""Add official disclosure document versions and extracted sections."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0018_official_disclosure_documents"
down_revision = "0017_official_disclosures"
branch_labels = None
depends_on = None


def _is_postgresql():
    bind = op.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _uuid_type():
    if _is_postgresql():
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _uuid_default():
    if _is_postgresql():
        return sa.text("gen_random_uuid()")
    return None


def _json_type():
    if _is_postgresql():
        return postgresql.JSONB()
    return sa.JSON()


def upgrade():
    uuid_type = _uuid_type()
    op.create_table(
        "official_disclosure_documents",
        sa.Column("id", uuid_type, primary_key=True, server_default=_uuid_default()),
        sa.Column(
            "official_disclosure_id",
            uuid_type,
            sa.ForeignKey("official_disclosures.id"),
            nullable=False,
        ),
        sa.Column("attachment_url", sa.String(2048), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
        sa.Column("provider_size", sa.Integer(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_modified", sa.String(128), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extraction_status", sa.String(32), nullable=False),
        sa.Column("extraction_method", sa.String(64), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "official_disclosure_id",
            "sha256",
            name="uq_official_disclosure_documents_version",
        ),
    )
    op.create_index(
        "ix_official_disclosure_documents_official_disclosure_id",
        "official_disclosure_documents",
        ["official_disclosure_id"],
    )

    op.create_table(
        "official_disclosure_sections",
        sa.Column("id", uuid_type, primary_key=True, server_default=_uuid_default()),
        sa.Column(
            "document_id",
            uuid_type,
            sa.ForeignKey("official_disclosure_documents.id"),
            nullable=False,
        ),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(512), nullable=False),
        sa.Column("topic", sa.String(64), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "document_id",
            "section_index",
            name="uq_official_disclosure_sections_index",
        ),
    )
    op.create_index(
        "ix_official_disclosure_sections_document_id",
        "official_disclosure_sections",
        ["document_id"],
    )


def downgrade():
    op.drop_index(
        "ix_official_disclosure_sections_document_id",
        table_name="official_disclosure_sections",
    )
    op.drop_table("official_disclosure_sections")
    op.drop_index(
        "ix_official_disclosure_documents_official_disclosure_id",
        table_name="official_disclosure_documents",
    )
    op.drop_table("official_disclosure_documents")
