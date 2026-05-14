import hmac
import re
import secrets
from typing import Any
from datetime import datetime, time, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
from app.models import (
    Category,
    IntegrationConnection,
    OCRResult,
    Receipt,
    ReceiptImage,
    Subscription,
    TelegramMapping,
    TelegramMessage,
    User,
    now_utc,
)
from app.ocr_client import OCRClient, OCRClientError, get_ocr_client
from app.security import hash_session_token
from app.storage import LocalReceiptStorage, get_storage
from app.telegram_client import TelegramClient, get_telegram_client
from app.upload_validation import upload_error, validate_image_bytes


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


class TelegramLinkRequest(BaseModel):
    pass


class TelegramUpdatePayload(BaseModel):
    update_id: int
    message: dict[str, Any] | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def structured_http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        error = exc.detail
    else:
        error = {
            "code": "request_error",
            "message": str(exc.detail) if exc.detail else "Request failed.",
        }
    return JSONResponse(status_code=exc.status_code, content={"error": error}, headers=exc.headers)


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


def parse_optional_datetime(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def new_telegram_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_telegram_code(user_id: str, code: str) -> str:
    return hash_session_token(f"telegram:{user_id}:{code}")


def verify_telegram_code(mapping: TelegramMapping, text: str | None) -> bool:
    if not mapping.verification_code_hash or not text:
        return False
    codes = re.findall(r"\b\d{6}\b", text)
    return any(
        hmac.compare_digest(mapping.verification_code_hash, hash_telegram_code(mapping.user_id, code))
        for code in codes
    )


def require_telegram_webhook_secret(x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> None:
    if not settings.telegram_webhook_secret:
        raise HTTPException(status_code=503, detail="Telegram webhook secret is not configured")
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token,
        settings.telegram_webhook_secret,
    ):
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")


async def send_telegram_reply(telegram_client: TelegramClient, chat_id: str | None, message: str) -> bool:
    if not chat_id:
        return False
    try:
        await telegram_client.send_message(chat_id, message)
    except Exception:
        return False
    return True


def telegram_start_text(message: dict[str, Any] | None) -> str | None:
    text = message.get("text") if message else None
    if not isinstance(text, str) or not text.startswith("/start"):
        return None
    return text


def telegram_sender(message: dict[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    if not message:
        return None, None, None
    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    user_id = sender.get("id")
    chat_id = chat.get("id")
    username = sender.get("username")
    return (
        str(user_id) if user_id is not None else None,
        str(chat_id) if chat_id is not None else None,
        str(username) if username else None,
    )


def telegram_message_id(message: dict[str, Any] | None) -> int | None:
    if not message:
        return None
    value = message.get("message_id")
    return value if isinstance(value, int) else None


def telegram_image_refs(message: dict[str, Any] | None) -> list[dict[str, str | None]]:
    if not message:
        return []
    refs: list[dict[str, str | None]] = []
    photos = message.get("photo")
    if isinstance(photos, list) and photos:
        photo_candidates = [photo for photo in photos if isinstance(photo, dict) and photo.get("file_id")]
        if photo_candidates:
            best_photo = max(
                photo_candidates,
                key=lambda photo: int(photo.get("file_size") or photo.get("width") or 0) * int(photo.get("height") or 1),
            )
            refs.append(
                {
                    "file_id": str(best_photo["file_id"]),
                    "filename": f"telegram-photo-{best_photo.get('file_unique_id') or best_photo['file_id']}.jpg",
                    "mime_type": "image/jpeg",
                }
            )
    document = message.get("document")
    if isinstance(document, dict) and document.get("file_id"):
        mime_type = document.get("mime_type")
        if isinstance(mime_type, str) and mime_type.startswith("image/"):
            refs.append(
                {
                    "file_id": str(document["file_id"]),
                    "filename": str(document.get("file_name") or f"telegram-document-{document['file_id']}.img"),
                    "mime_type": mime_type,
                }
            )
    return refs


def receipt_review_url(receipt_id: str) -> str:
    return f"{settings.frontend_origin.rstrip('/')}/receipts/{receipt_id}"


def format_cents(value: int | None) -> str:
    if value is None:
        return "the receipt total"
    return f"${value / 100:.2f}"


async def create_receipt_from_image(
    *,
    filename: str,
    contents: bytes,
    source: str,
    session: Session,
    ocr_client: OCRClient,
    storage: LocalReceiptStorage,
    current_user: User,
) -> dict:
    digest, detected_mime_type = validate_image_bytes(contents)

    existing_receipt = session.scalar(
        select(Receipt)
        .join(ReceiptImage)
        .where(
            Receipt.user_id == current_user.id,
            Receipt.source == source,
            Receipt.deleted_at.is_(None),
            ReceiptImage.sha256 == digest,
        )
        .order_by(desc(Receipt.created_at))
    )
    if existing_receipt is not None:
        return {
            "receipt_id": existing_receipt.id,
            "status": existing_receipt.status,
            "duplicate": True,
            "message": "This receipt image was already uploaded. Opening the existing receipt.",
        }

    receipt = Receipt(user_id=current_user.id, source=source, source_external_id=digest, status="processing")
    session.add(receipt)
    session.flush()

    storage_path = storage.save_original(current_user.id, receipt.id, filename, contents)
    image = ReceiptImage(
        receipt_id=receipt.id,
        storage_path=storage_path,
        original_filename=filename,
        mime_type=detected_mime_type,
        size_bytes=len(contents),
        sha256=digest,
    )
    session.add(image)
    session.flush()

    try:
        ocr_response = await ocr_client.parse_image(filename, detected_mime_type, contents)
    except OCRClientError as exc:
        receipt.status = "failed"
        receipt.notes = f"OCR failed: {exc}"
        receipt.updated_at = now_utc()
        session.commit()
        raise upload_error(
            502,
            "ocr_unavailable",
            "The receipt was saved, but OCR processing failed. Open the receipt to review or try again later.",
        ) from exc

    parsed = ocr_response.get("parsed", {})
    raw_text = ocr_response.get("raw_text", [])
    if not isinstance(raw_text, list):
        raw_text = [str(raw_text)]
    parsed_date = parse_optional_datetime(parsed.get("purchased_at"))

    receipt.amount_cents = parsed.get("total_cents")
    receipt.merchant_name = parsed.get("merchant_name")
    receipt.purchased_at = parsed_date
    receipt.status = "pending_review"
    receipt.updated_at = now_utc()

    ocr_result = OCRResult(
        receipt_id=receipt.id,
        raw_text="\n".join(str(item) for item in raw_text),
        raw_blocks={"raw_text": raw_text, "response": ocr_response},
        parsed_total_cents=parsed.get("total_cents"),
        parsed_date=parsed_date,
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
        "duplicate": False,
        "parsed": {
            "total_cents": receipt.amount_cents,
            "merchant_name": receipt.merchant_name,
            "purchased_at": receipt.purchased_at.isoformat() if receipt.purchased_at else None,
        },
        "parser_version": ocr_result.parser_version,
    }


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
    contents = await file.read()
    return await create_receipt_from_image(
        filename=file.filename or "receipt",
        contents=contents,
        source="web",
        session=session,
        ocr_client=ocr_client,
        storage=storage,
        current_user=current_user,
    )


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
    merchant: str | None = None,
    min_amount_cents: int | None = None,
    max_amount_cents: int | None = None,
    include_pending: bool = False,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    included_statuses = ["confirmed", "pending_review"] if include_pending else ["confirmed"]
    filter_conditions = [
        Receipt.user_id == current_user.id,
        Receipt.deleted_at.is_(None),
    ]
    parsed_start_date = parse_datetime_filter(start_date)
    parsed_end_date = parse_datetime_filter(end_date, end_of_day=True)
    if parsed_start_date is not None:
        filter_conditions.append(Receipt.purchased_at >= parsed_start_date)
    if parsed_end_date is not None:
        filter_conditions.append(Receipt.purchased_at <= parsed_end_date)
    if category_id:
        filter_conditions.append(Receipt.category_id == category_id)
    if source:
        filter_conditions.append(Receipt.source == source)
    if merchant:
        filter_conditions.append(Receipt.merchant_name.ilike(f"%{merchant.strip()}%"))
    if min_amount_cents is not None:
        filter_conditions.append(Receipt.amount_cents >= min_amount_cents)
    if max_amount_cents is not None:
        filter_conditions.append(Receipt.amount_cents <= max_amount_cents)

    conditions = [*filter_conditions, Receipt.status.in_(included_statuses), Receipt.amount_cents.is_not(None)]
    receipts = session.scalars(select(Receipt).where(*conditions)).all()
    confirmed_receipt_count = sum(1 for receipt in receipts if receipt.status == "confirmed")
    pending_review_count = session.scalar(
        select(func.count()).select_from(Receipt).where(*filter_conditions, Receipt.status == "pending_review")
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
        "confirmed_receipt_count": confirmed_receipt_count,
        "receipt_count": len(receipts),
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


@app.post("/integrations/telegram/link")
async def link_telegram(
    payload: TelegramLinkRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    _ = payload
    code = new_telegram_code()
    mapping = session.scalar(select(TelegramMapping).where(TelegramMapping.user_id == current_user.id))
    if mapping is None:
        mapping = TelegramMapping(user_id=current_user.id)
        session.add(mapping)
    else:
        mapping.telegram_user_id = None
        mapping.telegram_chat_id = None
        mapping.telegram_username = None
        mapping.verified_at = None
        mapping.linked_at = now_utc()
    mapping.verification_code_hash = hash_telegram_code(current_user.id, code)

    integration = session.scalar(
        select(IntegrationConnection).where(
            IntegrationConnection.user_id == current_user.id,
            IntegrationConnection.provider == "telegram",
        )
    )
    if integration is None:
        integration = IntegrationConnection(
            user_id=current_user.id,
            provider="telegram",
            status="pending",
            display_name="Waiting for Telegram verification",
        )
        session.add(integration)
    else:
        integration.status = "pending"
        integration.display_name = "Waiting for Telegram verification"
        integration.updated_at = now_utc()

    session.commit()
    return {
        "status": "pending_verification",
        "message": f"Send /start {code} to the Telegram bot.",
        "verification_code": code,
    }


@app.post("/telegram/webhook")
async def ingest_telegram_update(
    payload: TelegramUpdatePayload,
    _: None = Depends(require_telegram_webhook_secret),
    session: Session = Depends(get_session),
    ocr_client: OCRClient = Depends(get_ocr_client),
    storage: LocalReceiptStorage = Depends(get_storage),
    telegram_client: TelegramClient = Depends(get_telegram_client),
) -> dict:
    message_payload = payload.message
    telegram_user_id, telegram_chat_id, telegram_username = telegram_sender(message_payload)
    existing_message = session.scalar(
        select(TelegramMessage).where(TelegramMessage.telegram_update_id == payload.update_id)
    )
    if existing_message is not None:
        return {"status": "duplicate", "created_receipts": [], "duplicate": True}

    telegram_message = TelegramMessage(
        telegram_update_id=payload.update_id,
        telegram_message_id=telegram_message_id(message_payload),
        telegram_chat_id=telegram_chat_id,
        telegram_user_id=telegram_user_id,
        raw_payload=payload.model_dump(mode="json"),
        status="received",
    )
    session.add(telegram_message)
    session.flush()

    if not message_payload or not telegram_chat_id or not telegram_user_id:
        telegram_message.status = "ignored"
        telegram_message.processed_at = now_utc()
        session.commit()
        return {"status": "accepted", "created_receipts": []}

    mapping = session.scalar(
        select(TelegramMapping).where(
            TelegramMapping.telegram_user_id == telegram_user_id,
            TelegramMapping.verified_at.is_not(None),
        )
    )
    start_text = telegram_start_text(message_payload)
    if mapping is None and start_text:
        pending_mappings = session.scalars(
            select(TelegramMapping).where(
                TelegramMapping.verified_at.is_(None),
                TelegramMapping.verification_code_hash.is_not(None),
            )
        ).all()
        mapping = next((candidate for candidate in pending_mappings if verify_telegram_code(candidate, start_text)), None)
        existing_link = session.scalar(
            select(TelegramMapping).where(
                TelegramMapping.telegram_user_id == telegram_user_id,
                TelegramMapping.verified_at.is_not(None),
            )
        )
        if mapping is not None and existing_link is not None and existing_link.user_id != mapping.user_id:
            telegram_message.status = "failed"
            telegram_message.error_message = "Telegram account is already linked to another user"
            telegram_message.processed_at = now_utc()
            session.commit()
            await send_telegram_reply(
                telegram_client,
                telegram_chat_id,
                "This Telegram account is already linked to another Receipt Tracker user.",
            )
            return {"status": "failed", "created_receipts": []}

    if mapping is None:
        telegram_message.status = "ignored"
        telegram_message.processed_at = now_utc()
        session.commit()
        await send_telegram_reply(
            telegram_client,
            telegram_chat_id,
            "Telegram is not linked yet. Sign in to Receipt Tracker, open Integrations, connect Telegram, then send /start with your code here.",
        )
        return {"status": "accepted", "created_receipts": [], "linked": False}

    if mapping.verified_at is None:
        mapping.verified_at = now_utc()
        mapping.verification_code_hash = None
        mapping.telegram_user_id = telegram_user_id
        mapping.telegram_chat_id = telegram_chat_id
        mapping.telegram_username = telegram_username
        telegram_message.status = "linked"
        telegram_message.user_id = mapping.user_id
        integration = session.scalar(
            select(IntegrationConnection).where(
                IntegrationConnection.user_id == mapping.user_id,
                IntegrationConnection.provider == "telegram",
            )
        )
        display_name = f"@{telegram_username}" if telegram_username else f"Telegram user {telegram_user_id}"
        if integration is None:
            integration = IntegrationConnection(
                user_id=mapping.user_id,
                provider="telegram",
                status="active",
                display_name=display_name,
            )
            session.add(integration)
        else:
            integration.status = "active"
            integration.display_name = display_name
            integration.updated_at = now_utc()
        session.commit()
        if not telegram_image_refs(message_payload):
            await send_telegram_reply(telegram_client, telegram_chat_id, "Telegram connected. Send a receipt image when ready.")
            return {"status": "accepted", "created_receipts": [], "linked": True}

    user = session.get(User, mapping.user_id)
    if user is None:
        telegram_message.status = "failed"
        telegram_message.error_message = "Linked user not found"
        telegram_message.processed_at = now_utc()
        session.commit()
        await send_telegram_reply(telegram_client, telegram_chat_id, "Telegram is linked to an account that is no longer available.")
        return {"status": "failed", "created_receipts": []}

    image_refs = telegram_image_refs(message_payload)
    if not image_refs:
        telegram_message.user_id = user.id
        telegram_message.status = "ignored"
        telegram_message.processed_at = now_utc()
        session.commit()
        await send_telegram_reply(telegram_client, telegram_chat_id, "Send a JPG, PNG, or WebP receipt image.")
        return {"status": "accepted", "created_receipts": []}

    created_receipts: list[str] = []
    duplicate_count = 0
    errors: list[str] = []
    for image_ref in image_refs:
        filename = image_ref["filename"] or "telegram-receipt.img"
        try:
            contents = await telegram_client.download_file(str(image_ref["file_id"]))
            result = await create_receipt_from_image(
                filename=filename,
                contents=contents,
                source="telegram",
                session=session,
                ocr_client=ocr_client,
                storage=storage,
                current_user=user,
            )
        except HTTPException as exc:
            errors.append(str(exc.detail))
            continue
        except Exception as exc:
            errors.append(f"Telegram attachment could not be read: {exc}")
            continue

        created_receipts.append(result["receipt_id"])
        if result.get("duplicate"):
            duplicate_count += 1

    telegram_message.user_id = user.id
    telegram_message.processed_at = now_utc()
    if created_receipts:
        telegram_message.status = "duplicate" if duplicate_count == len(created_receipts) else "processed"
        session.commit()
        receipt = session.get(Receipt, created_receipts[0])
        total_text = format_cents(receipt.amount_cents if receipt else None)
        prefix = "Receipt already received." if duplicate_count == len(created_receipts) else "Receipt received."
        await send_telegram_reply(
            telegram_client,
            telegram_chat_id,
            f"{prefix} I found {total_text}. Review it here: {receipt_review_url(created_receipts[0])}",
        )
    else:
        telegram_message.status = "failed"
        telegram_message.error_message = "; ".join(errors)[:1000] if errors else "No processable image attachments"
        session.commit()
        await send_telegram_reply(
            telegram_client,
            telegram_chat_id,
            "I could not process that file. Please send a JPG, PNG, or WebP receipt image.",
        )

    return {
        "status": "accepted",
        "created_receipts": created_receipts,
        "duplicate_count": duplicate_count,
        "errors": errors,
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
