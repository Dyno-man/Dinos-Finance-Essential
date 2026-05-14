import uuid
from datetime import datetime, time, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuid_string() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (UniqueConstraint("session_token_hash", name="uq_sessions_token_hash"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship()


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, unique=True)
    plan_name: Mapped[str] = mapped_column(String, default="basic", nullable=False)
    status: Mapped[str] = mapped_column(String, default="basic", nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_categories_user_name"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str | None] = mapped_column(String)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint("source in ('web', 'telegram', 'gmail', 'manual')", name="ck_receipts_source"),
        CheckConstraint(
            "status in ('processing', 'pending_review', 'confirmed', 'failed')",
            name="ck_receipts_status",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_external_id: Mapped[str | None] = mapped_column(String)
    merchant_name: Mapped[str | None] = mapped_column(String)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amount_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="USD", nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    status: Mapped[str] = mapped_column(String, default="pending_review", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    images: Mapped[list["ReceiptImage"]] = relationship(back_populates="receipt")
    ocr_results: Mapped[list["OCRResult"]] = relationship(back_populates="receipt")


Index(
    "uq_receipts_user_source_external",
    Receipt.user_id,
    Receipt.source,
    Receipt.source_external_id,
    unique=True,
    sqlite_where=Receipt.source_external_id.is_not(None) & Receipt.deleted_at.is_(None),
    postgresql_where=Receipt.source_external_id.is_not(None) & Receipt.deleted_at.is_(None),
)


class ReceiptImage(Base):
    __tablename__ = "receipt_images"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("receipts.id"), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String)
    mime_type: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    receipt: Mapped[Receipt] = relationship(back_populates="images")


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("receipts.id"), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_blocks: Mapped[dict | None] = mapped_column(JSON)
    parsed_total_cents: Mapped[int | None] = mapped_column(Integer)
    parsed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parsed_merchant: Mapped[str | None] = mapped_column(String)
    parser_version: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    receipt: Mapped[Receipt] = relationship(back_populates="ocr_results")


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"
    __table_args__ = (
        CheckConstraint("provider in ('telegram', 'gmail')", name="ck_integration_connections_provider"),
        CheckConstraint("status in ('active', 'disabled', 'pending')", name="ck_integration_connections_status"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    display_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class TelegramMapping(Base):
    __tablename__ = "telegram_mappings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_telegram_mappings_user_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    telegram_user_id: Mapped[str | None] = mapped_column(String, unique=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String)
    telegram_username: Mapped[str | None] = mapped_column(String)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_code_hash: Mapped[str | None] = mapped_column(Text)


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    __table_args__ = (
        UniqueConstraint("telegram_update_id", name="uq_telegram_messages_update_id"),
        CheckConstraint(
            "status in ('received', 'linked', 'processed', 'duplicate', 'ignored', 'failed')",
            name="ck_telegram_messages_status",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    telegram_update_id: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer)
    telegram_chat_id: Mapped[str | None] = mapped_column(String)
    telegram_user_id: Mapped[str | None] = mapped_column(String)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class GmailConnection(Base):
    __tablename__ = "gmail_connections"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    google_email: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_label: Mapped[str] = mapped_column(String, default="Receipts", nullable=False)
    processed_label: Mapped[str] = mapped_column(String, default="ReceiptTrackerProcessed", nullable=False)
    ingestion_time_local: Mapped[time] = mapped_column(Time, default=time(2, 0), nullable=False)
    timezone: Mapped[str] = mapped_column(String, default="America/New_York", nullable=False)
    last_history_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class GmailProcessedMessage(Base):
    __tablename__ = "gmail_processed_messages"
    __table_args__ = (UniqueConstraint("user_id", "gmail_message_id", name="uq_gmail_processed_user_message"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    gmail_message_id: Mapped[str] = mapped_column(String, nullable=False)
    gmail_thread_id: Mapped[str | None] = mapped_column(String)
    receipt_id: Mapped[str | None] = mapped_column(ForeignKey("receipts.id"))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint("source in ('web', 'telegram', 'gmail', 'manual')", name="ck_ingestion_jobs_source"),
        CheckConstraint(
            "status in ('queued', 'processing', 'succeeded', 'failed', 'retrying')",
            name="ck_ingestion_jobs_status",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    receipt_id: Mapped[str | None] = mapped_column(ForeignKey("receipts.id"))
    source: Mapped[str] = mapped_column(String, nullable=False)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
