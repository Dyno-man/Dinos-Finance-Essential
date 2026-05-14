"""add telegram messages

Revision ID: 20260513_0004
Revises: 20260513_0003
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260513_0004"
down_revision = "20260513_0003"
branch_labels = None
depends_on = None


uuid_type = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    op.execute("alter table receipts drop constraint if exists ck_receipts_source")
    op.execute("update receipts set source = 'telegram' where source = 'signal'")
    op.create_check_constraint(
        "ck_receipts_source",
        "receipts",
        "source in ('web', 'telegram', 'gmail', 'manual')",
    )

    op.execute("alter table ingestion_jobs drop constraint if exists ck_ingestion_jobs_source")
    op.execute("update ingestion_jobs set source = 'telegram' where source = 'signal'")
    op.create_check_constraint(
        "ck_ingestion_jobs_source",
        "ingestion_jobs",
        "source in ('web', 'telegram', 'gmail', 'manual')",
    )

    op.execute("alter table integration_connections drop constraint if exists ck_integration_connections_provider")
    op.execute("update integration_connections set provider = 'telegram' where provider = 'signal'")
    op.create_check_constraint(
        "ck_integration_connections_provider",
        "integration_connections",
        "provider in ('telegram', 'gmail')",
    )

    op.execute(
        """
        do $$
        begin
            if to_regclass('telegram_mappings') is null and to_regclass('signal_mappings') is not null then
                alter table signal_mappings rename to telegram_mappings;
            end if;
        end $$;
        """
    )
    op.execute("alter table telegram_mappings drop constraint if exists uq_signal_mappings_signal_number")
    op.execute("alter table telegram_mappings add column if not exists telegram_user_id text")
    op.execute("alter table telegram_mappings add column if not exists telegram_chat_id text")
    op.execute("alter table telegram_mappings add column if not exists telegram_username text")
    op.execute("update telegram_mappings set verified_at = null, verification_code_hash = null")
    op.execute("alter table telegram_mappings drop column if exists signal_number")
    op.execute(
        """
        do $$
        begin
            if not exists (
                select 1 from pg_constraint where conname = 'uq_telegram_mappings_user_id'
            ) then
                alter table telegram_mappings add constraint uq_telegram_mappings_user_id unique (user_id);
            end if;
            if not exists (
                select 1 from pg_constraint where conname = 'uq_telegram_mappings_user'
            ) then
                alter table telegram_mappings add constraint uq_telegram_mappings_user unique (telegram_user_id);
            end if;
        end $$;
        """
    )

    op.create_table(
        "telegram_messages",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("telegram_update_id", sa.Integer(), nullable=False),
        sa.Column("telegram_message_id", sa.Integer(), nullable=True),
        sa.Column("telegram_chat_id", sa.Text(), nullable=True),
        sa.Column("telegram_user_id", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('received', 'linked', 'processed', 'duplicate', 'ignored', 'failed')",
            name="ck_telegram_messages_status",
        ),
    )
    op.create_unique_constraint(
        "uq_telegram_messages_update_id",
        "telegram_messages",
        ["telegram_update_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_telegram_messages_update_id", "telegram_messages", type_="unique")
    op.drop_table("telegram_messages")

    op.execute("alter table integration_connections drop constraint if exists ck_integration_connections_provider")
    op.execute("update integration_connections set provider = 'signal' where provider = 'telegram'")
    op.create_check_constraint(
        "ck_integration_connections_provider",
        "integration_connections",
        "provider in ('signal', 'gmail')",
    )

    op.execute("alter table ingestion_jobs drop constraint if exists ck_ingestion_jobs_source")
    op.execute("update ingestion_jobs set source = 'signal' where source = 'telegram'")
    op.create_check_constraint(
        "ck_ingestion_jobs_source",
        "ingestion_jobs",
        "source in ('web', 'signal', 'gmail', 'manual')",
    )

    op.execute("alter table receipts drop constraint if exists ck_receipts_source")
    op.execute("update receipts set source = 'signal' where source = 'telegram'")
    op.create_check_constraint(
        "ck_receipts_source",
        "receipts",
        "source in ('web', 'signal', 'gmail', 'manual')",
    )
