from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
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
from app.models import IntegrationConnection, OCRResult, Receipt, ReceiptImage, User
from app.ocr_client import OCRClient, OCRClientError, get_ocr_client
from app.storage import LocalReceiptStorage, get_storage
from app.upload_validation import read_valid_image


app = FastAPI(title="Receipt Finance Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
) -> dict:
    receipts = session.scalars(
        select(Receipt).where(Receipt.user_id == current_user.id, Receipt.deleted_at.is_(None))
    ).all()
    return {
        "receipts": [
            {
                "id": receipt.id,
                "source": receipt.source,
                "merchant_name": receipt.merchant_name,
                "amount_cents": receipt.amount_cents,
                "currency": receipt.currency,
                "status": receipt.status,
                "created_at": receipt.created_at.isoformat(),
            }
            for receipt in receipts
        ]
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
