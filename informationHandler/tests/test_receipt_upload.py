from io import BytesIO

import asyncio
from fastapi import HTTPException
import pytest
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import upload_receipt
from app.models import Base, OCRResult, Receipt, ReceiptImage
from app.storage import LocalReceiptStorage


class FakeOCRClient:
    async def health(self) -> bool:
        return True

    async def parse_image(self, filename: str, content_type: str | None, contents: bytes) -> dict:
        return {
            "raw_text": ["WALMART", "TOTAL", "12.34"],
            "parsed": {
                "total_cents": 1234,
                "merchant_name": "WALMART",
                "purchased_at": None,
            },
            "confidence": None,
            "parser_version": "easyocr_total_v1",
        }


class FailingOCRClient:
    async def parse_image(self, filename: str, content_type: str | None, contents: bytes) -> dict:
        from app.ocr_client import OCRClientError

        raise OCRClientError("ocr unavailable")


def make_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def make_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


class FakeUploadFile:
    def __init__(self, filename: str, contents: bytes, content_type: str) -> None:
        self.filename = filename
        self._contents = contents
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._contents


def upload_file(name: str, contents: bytes, content_type: str) -> FakeUploadFile:
    return FakeUploadFile(name, contents, content_type)


def test_upload_creates_receipt_image_and_ocr_result(tmp_path) -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        body = asyncio.run(
            upload_receipt(
                upload_file("receipt.png", make_png(), "image/png"),
                session,
                FakeOCRClient(),
                LocalReceiptStorage(str(tmp_path)),
            )
        )
        assert body["status"] == "pending_review"
        assert body["parsed"]["total_cents"] == 1234
        assert body["parser_version"] == "easyocr_total_v1"

        receipt = session.scalar(select(Receipt))
        assert receipt is not None
        assert receipt.amount_cents == 1234
        assert receipt.merchant_name == "WALMART"
        assert receipt.status == "pending_review"
        assert session.scalar(select(ReceiptImage)) is not None
        result = session.scalar(select(OCRResult))
        assert result is not None
        assert result.raw_text == "WALMART\nTOTAL\n12.34"
        assert result.parsed_total_cents == 1234


def test_invalid_image_is_rejected(tmp_path) -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                upload_receipt(
                    upload_file("receipt.txt", b"not an image", "text/plain"),
                    session,
                    FakeOCRClient(),
                    LocalReceiptStorage(str(tmp_path)),
                )
            )
        assert exc.value.status_code == 400


def test_ocr_failure_marks_receipt_failed(tmp_path) -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                upload_receipt(
                    upload_file("receipt.png", make_png(), "image/png"),
                    session,
                    FailingOCRClient(),
                    LocalReceiptStorage(str(tmp_path)),
                )
            )
        assert exc.value.status_code == 502

        receipt = session.scalar(select(Receipt))
        assert receipt is not None
        assert receipt.status == "failed"
        assert receipt.notes is not None
        assert "OCR failed" in receipt.notes
