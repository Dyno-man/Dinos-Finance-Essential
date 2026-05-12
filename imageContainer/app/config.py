import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "receipt-ocr")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    temp_upload_dir: str = os.getenv("OCR_TEMP_UPLOAD_DIR", "/tmp/receipt-ocr")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
