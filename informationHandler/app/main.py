from datetime import datetime, time, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    LoginRequest,
    RegisterRequest,
    get_current_user,
    get_subscription_plan,
    login_user,
    logout_user,
    register_user,
    safe_user,
)
from app.config import settings
from app.database import check_database, get_session
from app.models import Category, IntegrationConnection, OCRResult, Receipt, ReceiptImage, Subscription, User, now_utc
from app.ocr_client import OCRClient, OCRClientError, get_ocr_client
from app.storage import LocalReceiptStorage, get_storage
from app.upload_validation import read_valid_image


app = FastAPI(title="Receipt Finance Tracker API")

DEFAULT_CATEGORIES = [
    ("Grocery", "#0f766e"),
    ("Automobile", "#2563eb"),
    ("Restaurant", "#dc2626"),
    ("Recreation", "#7c3aed"),
    ("Household", "#ca8a04"),
    ("Health", "#059669"),
    ("Other", "#475467"),
]


class ReceiptUpdateRequest(BaseModel):
    merchant_name: str | None = Field(default=None, max_length=255)
    purchased_at: datetime | None = None
    amount_cents: int | None = Field(default=None, ge=0)
    category_id: str | None = None
    notes: str | None = None
    status: str | None = None


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=32)


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=32)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_default_categories(session: Session) -> None:
    existing = set(session.scalars(select(Category.name).where(Category.user_id.is_(None))).all())
    missing = [
        Category(user_id=None, name=name, color=color, is_default=True)
        for name, color in DEFAULT_CATEGORIES
        if name not in existing
    ]
    if missing:
        session.add_all(missing)
        session.commit()


def serialize_category(category: Category | None) -> dict | None:
    if category is None:
        return None
    return {
        "id": category.id,
        "name": category.name,
        "color": category.color,
        "is_default": category.is_default,
    }


def category_for_receipt(session: Session, receipt: Receipt) -> Category | None:
    if receipt.category_id is None:
        return None
    return session.get(Category, receipt.category_id)


def serialize_receipt(receipt: Receipt, category: Category | None = None) -> dict:
    return {
        "id": receipt.id,
        "source": receipt.source,
        "merchant_name": receipt.merchant_name,
        "purchased_at": receipt.purchased_at.isoformat() if receipt.purchased_at else None,
        "amount_cents": receipt.amount_cents,
        "currency": receipt.currency,
        "category_id": receipt.category_id,
        "category": serialize_category(category),
        "status": receipt.status,
        "notes": receipt.notes,
        "created_at": receipt.created_at.isoformat(),
        "updated_at": receipt.updated_at.isoformat(),
    }


def get_user_receipt(session: Session, current_user: User, receipt_id: str) -> Receipt:
    receipt = session.scalar(
        select(Receipt).where(
            Receipt.id == receipt_id,
            Receipt.user_id == current_user.id,
            Receipt.deleted_at.is_(None),
        )
    )
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


def validate_category_id(session: Session, current_user: User, category_id: str | None) -> str | None:
    if category_id is None:
        return None
    category = session.scalar(
        select(Category).where(
            Category.id == category_id,
            or_(Category.user_id == current_user.id, Category.user_id.is_(None)),
        )
    )
    if category is None:
        raise HTTPException(status_code=400, detail="Category not found")
    return category.id


def parse_datetime_filter(value: str | None, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    if len(value) == 10:
        date_value = datetime.fromisoformat(value).date()
        return datetime.combine(date_value, time.max if end_of_day else time.min, tzinfo=timezone.utc)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "receipt-api"}


@app.get("/health/deep")
async def deep_health(ocr_client: OCRClient = Depends(get_ocr_client)) -> dict[str, bool]:
    database_ok = False
    ocr_ok = False

    try:
        database_ok = check_database()
    except Exception:
        database_ok = False

    try:
        ocr_ok = await ocr_client.health()
    except Exception:
        ocr_ok = False

    return {"database": database_ok, "ocr": ocr_ok}


@app.post("/auth/register")
async def register(
    payload: RegisterRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> dict:
    return register_user(payload, response, session)


@app.post("/auth/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict:
    return login_user(payload, response, request, session)


@app.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict:
    return logout_user(request, response, session)


@app.get("/auth/me")
async def me(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    return safe_user(current_user, get_subscription_plan(session, current_user.id))


@app.post("/receipts/upload")
async def upload_receipt(
    file: UploadFile,
    session: Session = Depends(get_session),
    ocr_client: OCRClient = Depends(get_ocr_client),
    storage: LocalReceiptStorage = Depends(get_storage),
    current_user: User = Depends(get_current_user),
) -> dict:
    contents, digest = await read_valid_image(file)

    receipt = Receipt(user_id=current_user.id, source="web", status="processing")
    session.add(receipt)
    session.flush()

    storage_path = storage.save_original(current_user.id, receipt.id, file.filename or "receipt", contents)
    image = ReceiptImage(
        receipt_id=receipt.id,
        storage_path=storage_path,
        original_filename=file.filename,
        mime_type=file.content_type,
        size_bytes=len(contents),
        sha256=digest,
    )
    session.add(image)
    session.flush()

    try:
        ocr_response = await ocr_client.parse_image(file.filename or "receipt", file.content_type, contents)
    except OCRClientError as exc:
        receipt.status = "failed"
        receipt.notes = f"OCR failed: {exc}"
        session.commit()
        raise HTTPException(status_code=502, detail="OCR service failed") from exc

    parsed = ocr_response.get("parsed", {})
    raw_text = ocr_response.get("raw_text", [])
    if not isinstance(raw_text, list):
        raw_text = [str(raw_text)]

    receipt.amount_cents = parsed.get("total_cents")
    receipt.merchant_name = parsed.get("merchant_name")
    receipt.status = "pending_review"

    ocr_result = OCRResult(
        receipt_id=receipt.id,
        raw_text="\n".join(str(item) for item in raw_text),
        raw_blocks={"raw_text": raw_text},
        parsed_total_cents=parsed.get("total_cents"),
        parsed_merchant=parsed.get("merchant_name"),
        parser_version=ocr_response.get("parser_version", "unknown"),
        confidence=ocr_response.get("confidence"),
    )
    session.add(ocr_result)
    session.commit()
    session.refresh(receipt)

    return {
        "receipt_id": receipt.id,
        "status": receipt.status,
        "parsed": {
            "total_cents": receipt.amount_cents,
            "merchant_name": receipt.merchant_name,
            "purchased_at": parsed.get("purchased_at"),
        },
        "parser_version": ocr_result.parser_version,
    }


@app.get("/receipts")
async def list_receipts(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    start_date: str | None = None,
    end_date: str | None = None,
    category_id: str | None = None,
    merchant: str | None = None,
    source: str | None = None,
    status: str | None = None,
    min_amount_cents: int | None = None,
    max_amount_cents: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    conditions = [Receipt.user_id == current_user.id, Receipt.deleted_at.is_(None)]
    parsed_start_date = parse_datetime_filter(start_date)
    parsed_end_date = parse_datetime_filter(end_date, end_of_day=True)
    if parsed_start_date is not None:
        conditions.append(Receipt.purchased_at >= parsed_start_date)
    if parsed_end_date is not None:
        conditions.append(Receipt.purchased_at <= parsed_end_date)
    if category_id:
        conditions.append(Receipt.category_id == category_id)
    if merchant:
        conditions.append(Receipt.merchant_name.ilike(f"%{merchant.strip()}%"))
    if source:
        conditions.append(Receipt.source == source)
    if status:
        conditions.append(Receipt.status == status)
    if min_amount_cents is not None:
        conditions.append(Receipt.amount_cents >= min_amount_cents)
    if max_amount_cents is not None:
        conditions.append(Receipt.amount_cents <= max_amount_cents)

    total = session.scalar(select(func.count()).select_from(Receipt).where(*conditions)) or 0
    receipts = session.scalars(
        select(Receipt).where(*conditions).order_by(desc(Receipt.created_at)).limit(limit).offset(offset)
    ).all()
    categories = {
        category.id: category
        for category in session.scalars(
            select(Category).where(Category.id.in_([receipt.category_id for receipt in receipts if receipt.category_id]))
        ).all()
    }
    return {
        "receipts": [serialize_receipt(receipt, categories.get(receipt.category_id)) for receipt in receipts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/receipts/{receipt_id}")
async def get_receipt_detail(
    receipt_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    receipt = get_user_receipt(session, current_user, receipt_id)
    images = session.scalars(select(ReceiptImage).where(ReceiptImage.receipt_id == receipt.id)).all()
    ocr_result = session.scalar(
        select(OCRResult).where(OCRResult.receipt_id == receipt.id).order_by(desc(OCRResult.created_at))
    )
    return {
        "receipt": serialize_receipt(receipt, category_for_receipt(session, receipt)),
        "images": [
            {
                "id": image.id,
                "original_filename": image.original_filename,
                "mime_type": image.mime_type,
                "size_bytes": image.size_bytes,
                "created_at": image.created_at.isoformat(),
                "url": f"/receipts/{receipt.id}/image",
            }
            for image in images
        ],
        "ocr_result": {
            "id": ocr_result.id,
            "raw_text": ocr_result.raw_text,
            "parsed_total_cents": ocr_result.parsed_total_cents,
            "parsed_merchant": ocr_result.parsed_merchant,
            "parser_version": ocr_result.parser_version,
            "confidence": float(ocr_result.confidence) if ocr_result.confidence is not None else None,
            "created_at": ocr_result.created_at.isoformat(),
        }
        if ocr_result is not None
        else None,
    }


@app.patch("/receipts/{receipt_id}")
async def update_receipt(
    receipt_id: str,
    payload: ReceiptUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    receipt = get_user_receipt(session, current_user, receipt_id)
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes:
        receipt.category_id = validate_category_id(session, current_user, changes["category_id"])
    if "merchant_name" in changes:
        receipt.merchant_name = changes["merchant_name"]
    if "purchased_at" in changes:
        receipt.purchased_at = changes["purchased_at"]
    if "amount_cents" in changes:
        receipt.amount_cents = changes["amount_cents"]
    if "notes" in changes:
        receipt.notes = changes["notes"]
    if "status" in changes:
        if changes["status"] not in {"processing", "pending_review", "confirmed", "failed"}:
            raise HTTPException(status_code=400, detail="Invalid receipt status")
        receipt.status = changes["status"]
    receipt.updated_at = now_utc()
    session.commit()
    session.refresh(receipt)
    return {"receipt": serialize_receipt(receipt, category_for_receipt(session, receipt))}


@app.post("/receipts/{receipt_id}/confirm")
async def confirm_receipt(
    receipt_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    receipt = get_user_receipt(session, current_user, receipt_id)
    receipt.status = "confirmed"
    receipt.updated_at = now_utc()
    session.commit()
    session.refresh(receipt)
    return {"receipt": serialize_receipt(receipt, category_for_receipt(session, receipt))}


@app.delete("/receipts/{receipt_id}")
async def delete_receipt(
    receipt_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    receipt = get_user_receipt(session, current_user, receipt_id)
    receipt.deleted_at = now_utc()
    receipt.updated_at = now_utc()
    session.commit()
    return {"ok": True}


@app.get("/receipts/{receipt_id}/image")
async def get_receipt_image(
    receipt_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FileResponse:
    receipt = get_user_receipt(session, current_user, receipt_id)
    image = session.scalar(select(ReceiptImage).where(ReceiptImage.receipt_id == receipt.id).order_by(ReceiptImage.created_at))
    if image is None:
        raise HTTPException(status_code=404, detail="Receipt image not found")
    path = Path(image.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Receipt image file not found")
    return FileResponse(path, media_type=image.mime_type, filename=image.original_filename)


@app.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    ensure_default_categories(session)
    categories = session.scalars(
        select(Category)
        .where(or_(Category.user_id == current_user.id, Category.user_id.is_(None)))
        .order_by(Category.is_default.desc(), Category.name)
    ).all()
    return {"categories": [serialize_category(category) for category in categories]}


@app.post("/categories")
async def create_category(
    payload: CategoryCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    category = Category(user_id=current_user.id, name=payload.name.strip(), color=payload.color, is_default=False)
    session.add(category)
    session.commit()
    session.refresh(category)
    return {"category": serialize_category(category)}


@app.patch("/categories/{category_id}")
async def update_category(
    category_id: str,
    payload: CategoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    category = session.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == current_user.id)
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        category.name = changes["name"].strip()
    if "color" in changes:
        category.color = changes["color"]
    session.commit()
    session.refresh(category)
    return {"category": serialize_category(category)}


@app.get("/analytics/summary")
async def analytics_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    category_id: str | None = None,
    source: str | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    conditions = [
        Receipt.user_id == current_user.id,
        Receipt.deleted_at.is_(None),
        Receipt.status == "confirmed",
        Receipt.amount_cents.is_not(None),
    ]
    parsed_start_date = parse_datetime_filter(start_date)
    parsed_end_date = parse_datetime_filter(end_date, end_of_day=True)
    if parsed_start_date is not None:
        conditions.append(Receipt.purchased_at >= parsed_start_date)
    if parsed_end_date is not None:
        conditions.append(Receipt.purchased_at <= parsed_end_date)
    if category_id:
        conditions.append(Receipt.category_id == category_id)
    if source:
        conditions.append(Receipt.source == source)

    receipts = session.scalars(select(Receipt).where(*conditions)).all()
    pending_review_count = session.scalar(
        select(func.count()).select_from(Receipt).where(
            Receipt.user_id == current_user.id,
            Receipt.deleted_at.is_(None),
            Receipt.status == "pending_review",
        )
    ) or 0
    all_receipt_count = session.scalar(
        select(func.count()).select_from(Receipt).where(Receipt.user_id == current_user.id, Receipt.deleted_at.is_(None))
    ) or 0
    categories = {
        category.id: category
        for category in session.scalars(select(Category).where(Category.id.in_([r.category_id for r in receipts if r.category_id]))).all()
    }

    monthly: dict[str, int] = {}
    category_totals: dict[str, dict] = {}
    merchant_totals: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    total_cents = 0
    for receipt in receipts:
        amount = receipt.amount_cents or 0
        total_cents += amount
        date_value = receipt.purchased_at or receipt.created_at
        month_key = date_value.strftime("%Y-%m")
        monthly[month_key] = monthly.get(month_key, 0) + amount
        category = categories.get(receipt.category_id)
        category_name = category.name if category else "Uncategorized"
        category_totals.setdefault(
            category_name,
            {"category_id": receipt.category_id, "name": category_name, "amount_cents": 0, "color": category.color if category else None},
        )
        category_totals[category_name]["amount_cents"] += amount
        merchant_name = receipt.merchant_name or "Unknown merchant"
        merchant_totals[merchant_name] = merchant_totals.get(merchant_name, 0) + amount
        source_counts[receipt.source] = source_counts.get(receipt.source, 0) + 1

    return {
        "total_cents": total_cents,
        "confirmed_receipt_count": len(receipts),
        "receipt_count": all_receipt_count,
        "average_receipt_cents": round(total_cents / len(receipts)) if receipts else 0,
        "pending_review_count": pending_review_count,
        "monthly_spend": [{"month": key, "amount_cents": value} for key, value in sorted(monthly.items())],
        "category_spend": sorted(category_totals.values(), key=lambda item: item["amount_cents"], reverse=True),
        "merchant_spend": [
            {"merchant_name": key, "amount_cents": value}
            for key, value in sorted(merchant_totals.items(), key=lambda item: item[1], reverse=True)
        ][:10],
        "source_counts": [{"source": key, "count": value} for key, value in sorted(source_counts.items())],
    }


@app.get("/billing/summary")
async def billing_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == current_user.id))
    return {
        "plan_name": subscription.plan_name if subscription else "basic",
        "status": subscription.status if subscription else "basic",
        "current_period_end": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
        "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False,
    }


@app.get("/integrations")
async def list_integrations(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    integrations = session.scalars(
        select(IntegrationConnection).where(IntegrationConnection.user_id == current_user.id)
    ).all()
    return {
        "integrations": [
            {
                "id": integration.id,
                "provider": integration.provider,
                "status": integration.status,
                "display_name": integration.display_name,
                "created_at": integration.created_at.isoformat(),
            }
            for integration in integrations
        ]
    }


@app.post("/upload")
async def legacy_upload(
    file: UploadFile,
    session: Session = Depends(get_session),
    ocr_client: OCRClient = Depends(get_ocr_client),
    storage: LocalReceiptStorage = Depends(get_storage),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await upload_receipt(file, session, ocr_client, storage, current_user)
    return result
