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

        body = asyncio.run(analytics_summary(current_user=grant, session=session))

        assert body["total_cents"] == 2500
        assert body["confirmed_receipt_count"] == 1
        assert body["receipt_count"] == 1
        assert body["pending_review_count"] == 1
        assert body["category_spend"][0]["name"] == "Grocery"


def test_analytics_can_include_pending_review_receipts() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session, "grant")
        confirmed = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Market",
            amount_cents=2500,
            purchased_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )
        pending = Receipt(
            user_id=user.id,
            source="web",
            status="pending_review",
            merchant_name="Market",
            amount_cents=1100,
            purchased_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        )
        processing = Receipt(user_id=user.id, source="web", status="processing", amount_cents=9999)
        failed = Receipt(user_id=user.id, source="web", status="failed", amount_cents=9999)
        session.add_all([confirmed, pending, processing, failed])
        session.commit()

        default_body = asyncio.run(analytics_summary(current_user=user, session=session))
        included_body = asyncio.run(analytics_summary(include_pending=True, current_user=user, session=session))

        assert default_body["total_cents"] == 2500
        assert default_body["confirmed_receipt_count"] == 1
        assert default_body["pending_review_count"] == 1
        assert default_body["receipt_count"] == 1
        assert included_body["total_cents"] == 3600
        assert included_body["confirmed_receipt_count"] == 1
        assert included_body["pending_review_count"] == 1
        assert included_body["receipt_count"] == 2
        assert included_body["average_receipt_cents"] == 1800


def test_analytics_filters_match_receipt_list_filters() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session, "grant")
        other = make_user(session, "other")
        grocery = Category(user_id=user.id, name="Grocery", color="#0f766e")
        restaurant = Category(user_id=user.id, name="Restaurant", color="#dc2626")
        session.add_all([grocery, restaurant])
        session.flush()
        included = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=2500,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )
        pending_included = Receipt(
            user_id=user.id,
            source="web",
            status="pending_review",
            merchant_name="Corner Market",
            amount_cents=1200,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )
        wrong_category = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=3000,
            category_id=restaurant.id,
            purchased_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
        )
        wrong_merchant = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Fuel Stop",
            amount_cents=2500,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )
        wrong_source = Receipt(
            user_id=user.id,
            source="gmail",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=2500,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )
        too_small = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=500,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )
        too_large = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=5000,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )
        outside_date = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=2500,
            category_id=grocery.id,
            purchased_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        )
        no_amount = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )
        deleted = Receipt(
            user_id=user.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=2500,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
            deleted_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
        )
        other_user = Receipt(
            user_id=other.id,
            source="web",
            status="confirmed",
            merchant_name="Corner Market",
            amount_cents=2500,
            category_id=grocery.id,
            purchased_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )
        session.add_all(
            [
                included,
                pending_included,
                wrong_category,
                wrong_merchant,
                wrong_source,
                too_small,
                too_large,
                outside_date,
                no_amount,
                deleted,
                other_user,
            ]
        )
        session.commit()

        analytics = asyncio.run(
            analytics_summary(
                start_date="2026-05-01",
                end_date="2026-05-31",
                category_id=grocery.id,
                source="web",
                merchant="Corner",
                min_amount_cents=1000,
                max_amount_cents=3000,
                include_pending=True,
                current_user=user,
                session=session,
            )
        )
        listed = asyncio.run(
            list_receipts(
                user,
                session,
                start_date="2026-05-01",
                end_date="2026-05-31",
                category_id=grocery.id,
                merchant="Corner",
                source="web",
                min_amount_cents=1000,
                max_amount_cents=3000,
            )
        )
        listed_spend = sum(receipt["amount_cents"] or 0 for receipt in listed["receipts"] if receipt["status"] in {"confirmed", "pending_review"})

        assert listed["total"] == 2
        assert analytics["receipt_count"] == 2
        assert analytics["total_cents"] == 3700
        assert analytics["total_cents"] == listed_spend
        assert analytics["confirmed_receipt_count"] == 1
        assert analytics["pending_review_count"] == 1
        assert analytics["monthly_spend"] == [{"month": "2026-05", "amount_cents": 3700}]
        assert analytics["category_spend"][0]["name"] == "Grocery"
        assert analytics["merchant_spend"] == [{"merchant_name": "Corner Market", "amount_cents": 3700}]
        assert analytics["source_counts"] == [{"source": "web", "count": 2}]


def test_empty_analytics_returns_zero_totals() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = make_user(session, "grant")

        body = asyncio.run(analytics_summary(current_user=user, session=session))

        assert body["total_cents"] == 0
        assert body["confirmed_receipt_count"] == 0
        assert body["receipt_count"] == 0
        assert body["average_receipt_cents"] == 0
        assert body["pending_review_count"] == 0
        assert body["monthly_spend"] == []
        assert body["category_spend"] == []
        assert body["merchant_spend"] == []
        assert body["source_counts"] == []
