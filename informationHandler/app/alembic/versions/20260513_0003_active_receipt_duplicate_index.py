"""scope receipt duplicate index to active receipts

Revision ID: 20260513_0003
Revises: 20260512_0002
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa


revision = "20260513_0003"
down_revision = "20260512_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_receipts_user_source_external", table_name="receipts")
    op.create_index(
        "uq_receipts_user_source_external",
        "receipts",
        ["user_id", "source", "source_external_id"],
        unique=True,
        postgresql_where=sa.text("source_external_id is not null and deleted_at is null"),
        sqlite_where=sa.text("source_external_id is not null and deleted_at is null"),
    )


def downgrade() -> None:
    op.drop_index("uq_receipts_user_source_external", table_name="receipts")
    op.create_index(
        "uq_receipts_user_source_external",
        "receipts",
        ["user_id", "source", "source_external_id"],
        unique=True,
        postgresql_where=sa.text("source_external_id is not null"),
        sqlite_where=sa.text("source_external_id is not null"),
    )
