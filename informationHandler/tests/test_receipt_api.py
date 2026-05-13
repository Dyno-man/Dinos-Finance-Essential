import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import (
    ReceiptUpdateRequest,
    analytics_summary,
    confirm_receipt,
    create_category,
    delete_receipt,
    get_receipt_detail,
    list_categories,
    list_receipts,
    update_receipt,
)
from app.main import CategoryCreateRequest
from app.models import Base, Category, OCRResult, Receipt, User


def make_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def make_user(session: Session, username: str) -> User:
    user = User(username=username, email=f"{username}@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def test_receipt_detail_is_user_scoped() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        grant = make_user(session, "grant")
        other = make_user(session, "other")
        receipt = Receipt(user_id=other.id, source="web", status="pending_review", merchant_name="Theirs")
        session.add(receipt)
        session.commit()

        with pytest.raises(Exception) as exc:
            asyncio.run(get_receipt_detail(receipt.id, grant, session))
        assert getattr(exc.value, "status_code", None) == 404


def test_update_confirm_and_soft_delete_receipt() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session, "grant")
        category = Category(user_id=user.id, name="Coffee", color="#0f766e")
        receipt = Receipt(user_id=user.id, source="web", status="pending_review")
        session.add_all([category, receipt])
        session.commit()

        body = asyncio.run(
            update_receipt(
                receipt.id,
                ReceiptUpdateRequest(
                    merchant_name="Cafe",
                    purchased_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
                    amount_cents=1299,
                    category_id=category.id,
                    notes="Team breakfast",
                ),
                user,
                session,
            )
        )
        assert body["receipt"]["merchant_name"] == "Cafe"
        assert body["receipt"]["amount_cents"] == 1299
        assert body["receipt"]["category"]["name"] == "Coffee"

        confirmed = asyncio.run(confirm_receipt(receipt.id, user, session))
        assert confirmed["receipt"]["status"] == "confirmed"

        assert asyncio.run(delete_receipt(receipt.id, user, session)) == {"ok": True}
        listed = asyncio.run(list_receipts(user, session))
        assert listed["receipts"] == []


def test_categories_include_defaults_and_user_categories() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session, "grant")
        created = asyncio.run(create_category(CategoryCreateRequest(name="Work", color="#2563eb"), user, session))

        body = asyncio.run(list_categories(user, session))
        names = {category["name"] for category in body["categories"]}

        assert created["category"]["name"] == "Work"
        assert "Grocery" in names
        assert "Other" in names
        assert "Work" in names


def test_analytics_only_uses_current_user_confirmed_receipts() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        grant = make_user(session, "grant")
        other = make_user(session, "other")
        category = Category(user_id=grant.id, name="Grocery", color="#0f766e")
        session.add(category)
        session.flush()
        receipt = Receipt(
            user_id=grant.id,
            source="web",
            status="confirmed",
            merchant_name="Market",
            amount_cents=2500,
            category_id=category.id,
            purchased_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )
        pending = Receipt(user_id=grant.id, source="web", status="pending_review", amount_cents=9900)
        other_receipt = Receipt(user_id=other.id, source="web", status="confirmed", amount_cents=9999)
        ocr_result = OCRResult(
            receipt=receipt,
            raw_text="Market\nTOTAL\n25.00",
            parsed_total_cents=2500,
            parser_version="easyocr_total_v1",
        )
        session.add_all([receipt, pending, other_receipt, ocr_result])
        session.commit()

        body = asyncio.run(analytics_summary(None, None, None, None, grant, session))

        assert body["total_cents"] == 2500
        assert body["confirmed_receipt_count"] == 1
        assert body["receipt_count"] == 2
        assert body["pending_review_count"] == 1
        assert body["category_spend"][0]["name"] == "Grocery"
