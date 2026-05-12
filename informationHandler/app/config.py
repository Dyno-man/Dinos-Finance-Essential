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

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
