import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "receipt-api")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@db:5432/receipts",
    )
    ocr_service_url: str = os.getenv("OCR_SERVICE_URL", "http://ocr:80")
    receipt_storage_path: str = os.getenv("RECEIPT_STORAGE_PATH", "/data/receipt_uploads")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    dev_username: str = os.getenv("DEV_USER_USERNAME", "dev")
    dev_email: str = os.getenv("DEV_USER_EMAIL", "dev@example.local")
    dev_password_hash: str = os.getenv("DEV_USER_PASSWORD_HASH", "dev-only-not-authenticated")
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "receipt_tracker_session")
    session_secret: str = os.getenv("SESSION_SECRET", "dev-session-secret-change-me")
    session_ttl_days: int = int(os.getenv("SESSION_TTL_DAYS", "7"))
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "lax")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    frontend_origins: str = os.getenv("FRONTEND_ORIGINS", "")
    login_rate_limit_attempts: int = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
    login_rate_limit_window_seconds: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_webhook_secret: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    telegram_reply_enabled: bool = os.getenv("TELEGRAM_REPLY_ENABLED", "true").lower() == "true"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        configured = [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]
        origins = configured or [self.frontend_origin]
        for local_origin in ("http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"):
            if local_origin not in origins:
                origins.append(local_origin)
        return origins


settings = Settings()
