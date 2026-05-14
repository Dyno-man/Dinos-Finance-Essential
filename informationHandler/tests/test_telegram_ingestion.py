import asyncio
from io import BytesIO

from fastapi import HTTPException
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.main import TelegramLinkRequest, TelegramUpdatePayload, ingest_telegram_update, link_telegram
from app.main import require_telegram_webhook_secret
from app.models import Base, IntegrationConnection, OCRResult, Receipt, TelegramMapping, TelegramMessage, User
from app.storage import LocalReceiptStorage


class FakeOCRClient:
    def __init__(self) -> None:
        self.calls = 0

    async def parse_image(self, filename: str, content_type: str | None, contents: bytes) -> dict:
        self.calls += 1
        return {
            "raw_text": ["TARGET", "TOTAL", "12.34"],
            "parsed": {
                "total_cents": 1234,
                "merchant_name": "TARGET",
                "purchased_at": None,
            },
            "confidence": None,
            "parser_version": "easyocr_total_v1",
        }


class FakeTelegramClient:
    def __init__(self, file_contents: bytes | None = None) -> None:
        self.messages: list[tuple[str, str]] = []
        self.file_contents = file_contents or make_png()
        self.downloads = 0

    async def send_message(self, chat_id: str, message: str) -> None:
        self.messages.append((chat_id, message))

    async def download_file(self, file_id: str) -> bytes:
        self.downloads += 1
        return self.file_contents


def make_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def make_user(session: Session, username: str = "grant") -> User:
    user = User(username=username, email=f"{username}@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def make_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def telegram_payload(update_id: int, text: str | None = None, photo: bool = False) -> TelegramUpdatePayload:
    message: dict = {
        "message_id": update_id + 100,
        "from": {"id": 123456, "username": "receiptuser"},
        "chat": {"id": 987654, "type": "private"},
    }
    if text is not None:
        message["text"] = text
    if photo:
        message["photo"] = [
            {"file_id": "small-file", "file_unique_id": "small", "width": 100, "height": 100},
            {"file_id": "large-file", "file_unique_id": "large", "width": 1000, "height": 1000},
        ]
    return TelegramUpdatePayload(update_id=update_id, message=message)


def test_telegram_link_and_verification_code_flow() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session)
        telegram_client = FakeTelegramClient()

        link_body = asyncio.run(link_telegram(TelegramLinkRequest(), user, session))
        assert link_body["status"] == "pending_verification"
        code = link_body["verification_code"]

        body = asyncio.run(
            ingest_telegram_update(
                telegram_payload(1, f"/start {code}"),
                None,
                session,
                FakeOCRClient(),
                LocalReceiptStorage(),
                telegram_client,
            )
        )

        assert body["linked"] is True
        mapping = session.scalar(select(TelegramMapping).where(TelegramMapping.telegram_user_id == "123456"))
        assert mapping is not None
        assert mapping.verified_at is not None
        assert mapping.telegram_chat_id == "987654"
        integration = session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider == "telegram"))
        assert integration is not None
        assert integration.status == "active"
        assert telegram_client.messages[-1][1] == "Telegram connected. Send a receipt image when ready."


def test_unknown_telegram_sender_gets_linking_instructions() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        telegram_client = FakeTelegramClient()

        body = asyncio.run(
            ingest_telegram_update(
                telegram_payload(2, "hello"),
                None,
                session,
                FakeOCRClient(),
                LocalReceiptStorage(),
                telegram_client,
            )
        )

        assert body["created_receipts"] == []
        assert body["linked"] is False
        assert "not linked" in telegram_client.messages[-1][1]
        telegram_message = session.scalar(select(TelegramMessage).where(TelegramMessage.telegram_update_id == 2))
        assert telegram_message is not None
        assert telegram_message.status == "ignored"


def test_linked_telegram_image_creates_receipt_and_reply(tmp_path) -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session)
        session.add(
            TelegramMapping(
                user_id=user.id,
                telegram_user_id="123456",
                telegram_chat_id="987654",
                telegram_username="receiptuser",
                verified_at=user.created_at,
            )
        )
        session.commit()
        ocr_client = FakeOCRClient()
        telegram_client = FakeTelegramClient()

        body = asyncio.run(
            ingest_telegram_update(
                telegram_payload(3, photo=True),
                None,
                session,
                ocr_client,
                LocalReceiptStorage(str(tmp_path / "storage")),
                telegram_client,
            )
        )

        assert len(body["created_receipts"]) == 1
        assert ocr_client.calls == 1
        assert telegram_client.downloads == 1
        receipt = session.get(Receipt, body["created_receipts"][0])
        assert receipt is not None
        assert receipt.source == "telegram"
        assert receipt.amount_cents == 1234
        assert session.scalar(select(OCRResult).where(OCRResult.receipt_id == receipt.id)) is not None
        assert "Receipt received." in telegram_client.messages[-1][1]
        assert "$12.34" in telegram_client.messages[-1][1]


def test_telegram_update_id_duplicate_does_not_reprocess(tmp_path) -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session)
        session.add(TelegramMapping(user_id=user.id, telegram_user_id="123456", telegram_chat_id="987654", verified_at=user.created_at))
        session.add(
            TelegramMessage(
                telegram_update_id=4,
                telegram_message_id=104,
                telegram_chat_id="987654",
                telegram_user_id="123456",
                raw_payload={},
                status="processed",
            )
        )
        session.commit()
        ocr_client = FakeOCRClient()
        telegram_client = FakeTelegramClient()

        body = asyncio.run(
            ingest_telegram_update(
                telegram_payload(4, photo=True),
                None,
                session,
                ocr_client,
                LocalReceiptStorage(str(tmp_path)),
                telegram_client,
            )
        )

        assert body["duplicate"] is True
        assert ocr_client.calls == 0
        assert telegram_client.downloads == 0
        assert session.scalars(select(Receipt)).all() == []


def test_telegram_attachment_hash_duplicate_reuses_receipt(tmp_path) -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session)
        session.add(TelegramMapping(user_id=user.id, telegram_user_id="123456", telegram_chat_id="987654", verified_at=user.created_at))
        session.commit()
        ocr_client = FakeOCRClient()
        telegram_client = FakeTelegramClient()

        first = asyncio.run(
            ingest_telegram_update(
                telegram_payload(5, photo=True),
                None,
                session,
                ocr_client,
                LocalReceiptStorage(str(tmp_path / "storage")),
                telegram_client,
            )
        )
        second = asyncio.run(
            ingest_telegram_update(
                telegram_payload(6, photo=True),
                None,
                session,
                ocr_client,
                LocalReceiptStorage(str(tmp_path / "storage")),
                telegram_client,
            )
        )

        assert second["created_receipts"] == first["created_receipts"]
        assert second["duplicate_count"] == 1
        assert ocr_client.calls == 1
        assert telegram_client.downloads == 2
        assert len(session.scalars(select(Receipt)).all()) == 1


def test_telegram_webhook_secret_rejects_bad_secret() -> None:
    original_secret = settings.telegram_webhook_secret
    object.__setattr__(settings, "telegram_webhook_secret", "expected-secret")
    try:
        try:
            require_telegram_webhook_secret("wrong-secret")
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("bad Telegram webhook secret was accepted")
    finally:
        object.__setattr__(settings, "telegram_webhook_secret", original_secret)
