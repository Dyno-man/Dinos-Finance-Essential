"""initial schema

Revision ID: 20260512_0001
Revises:
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260512_0001"
down_revision = None
branch_labels = None
depends_on = None


uuid_type = postgresql.UUID(as_uuid=False)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.execute('create extension if not exists "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), server_default="user", nullable=False),
        *timestamps(),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.create_table(
        "categories",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_categories_user_name", "categories", ["user_id", "name"])

    op.create_table(
        "subscriptions",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("plan_name", sa.Text(), server_default="basic", nullable=False),
        sa.Column("status", sa.Text(), server_default="basic", nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *timestamps(),
    )
    op.create_unique_constraint("uq_subscriptions_stripe_customer", "subscriptions", ["stripe_customer_id"])
    op.create_unique_constraint("uq_subscriptions_stripe_subscription", "subscriptions", ["stripe_subscription_id"])

    op.create_table(
        "receipts",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_external_id", sa.Text(), nullable=True),
        sa.Column("merchant_name", sa.Text(), nullable=True),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.Text(), server_default="USD", nullable=False),
        sa.Column("category_id", uuid_type, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("status", sa.Text(), server_default="pending_review", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source in ('web', 'telegram', 'gmail', 'manual')", name="ck_receipts_source"),
        sa.CheckConstraint(
            "status in ('processing', 'pending_review', 'confirmed', 'failed')",
            name="ck_receipts_status",
        ),
    )
    op.create_index(
        "uq_receipts_user_source_external",
        "receipts",
        ["user_id", "source", "source_external_id"],
        unique=True,
        postgresql_where=sa.text("source_external_id is not null"),
    )

    op.create_table(
        "receipt_images",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("receipt_id", uuid_type, sa.ForeignKey("receipts.id"), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "ocr_results",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("receipt_id", uuid_type, sa.ForeignKey("receipts.id"), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("raw_blocks", postgresql.JSONB(), nullable=True),
        sa.Column("parsed_total_cents", sa.Integer(), nullable=True),
        sa.Column("parsed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parsed_merchant", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "integration_connections",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        *timestamps(),
        sa.CheckConstraint("provider in ('telegram', 'gmail')", name="ck_integration_connections_provider"),
        sa.CheckConstraint("status in ('active', 'disabled', 'pending')", name="ck_integration_connections_status"),
    )

    op.create_table(
        "telegram_mappings",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("telegram_user_id", sa.Text(), nullable=True),
        sa.Column("telegram_chat_id", sa.Text(), nullable=True),
        sa.Column("telegram_username", sa.Text(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_code_hash", sa.Text(), nullable=True),
    )
    op.create_unique_constraint("uq_telegram_mappings_user_id", "telegram_mappings", ["user_id"])
    op.create_unique_constraint("uq_telegram_mappings_user", "telegram_mappings", ["telegram_user_id"])

    op.create_table(
        "gmail_connections",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("google_email", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("receipt_label", sa.Text(), server_default="Receipts", nullable=False),
        sa.Column("processed_label", sa.Text(), server_default="ReceiptTrackerProcessed", nullable=False),
        sa.Column("ingestion_time_local", sa.Time(), server_default="02:00", nullable=False),
        sa.Column("timezone", sa.Text(), server_default="America/New_York", nullable=False),
        sa.Column("last_history_id", sa.Text(), nullable=True),
        *timestamps(),
    )

    op.create_table(
        "gmail_processed_messages",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("gmail_message_id", sa.Text(), nullable=False),
        sa.Column("gmail_thread_id", sa.Text(), nullable=True),
        sa.Column("receipt_id", uuid_type, sa.ForeignKey("receipts.id"), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_gmail_processed_user_message",
        "gmail_processed_messages",
        ["user_id", "gmail_message_id"],
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("receipt_id", uuid_type, sa.ForeignKey("receipts.id"), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *timestamps(),
        sa.CheckConstraint("source in ('web', 'telegram', 'gmail', 'manual')", name="ck_ingestion_jobs_source"),
        sa.CheckConstraint(
            "status in ('queued', 'processing', 'succeeded', 'failed', 'retrying')",
            name="ck_ingestion_jobs_status",
        ),
    )

    op.bulk_insert(
        sa.table(
            "categories",
            sa.column("name", sa.Text()),
            sa.column("is_default", sa.Boolean()),
        ),
        [
            {"name": "Grocery", "is_default": True},
            {"name": "Automobile", "is_default": True},
            {"name": "Restaurant", "is_default": True},
            {"name": "Recreation", "is_default": True},
            {"name": "Household", "is_default": True},
            {"name": "Health", "is_default": True},
            {"name": "Other", "is_default": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_constraint("uq_gmail_processed_user_message", "gmail_processed_messages", type_="unique")
    op.drop_table("gmail_processed_messages")
    op.drop_table("gmail_connections")
    op.drop_constraint("uq_telegram_mappings_user", "telegram_mappings", type_="unique")
    op.drop_constraint("uq_telegram_mappings_user_id", "telegram_mappings", type_="unique")
    op.drop_table("telegram_mappings")
    op.drop_table("integration_connections")
    op.drop_table("ocr_results")
    op.drop_table("receipt_images")
    op.drop_index("uq_receipts_user_source_external", table_name="receipts")
    op.drop_table("receipts")
    op.drop_constraint("uq_subscriptions_stripe_subscription", "subscriptions", type_="unique")
    op.drop_constraint("uq_subscriptions_stripe_customer", "subscriptions", type_="unique")
    op.drop_table("subscriptions")
    op.drop_constraint("uq_categories_user_name", "categories", type_="unique")
    op.drop_table("categories")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_table("users")
