from pathlib import Path
from tempfile import NamedTemporaryFile

import easyocr
from fastapi import FastAPI, HTTPException, UploadFile
from PIL import Image

from app.config import settings
from app.parser import PARSER_VERSION, find_total_cents


app = FastAPI(title="Receipt OCR Service")
reader = easyocr.Reader(["en"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/ocr/upload")
async def upload_for_ocr(file: UploadFile) -> dict:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")

    temp_dir = Path(settings.temp_upload_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "receipt").suffix or ".img"
    temp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as temp_file:
            temp_file.write(contents)
            temp_path = Path(temp_file.name)

        try:
            with Image.open(temp_path) as image:
                image.verify()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc

        raw_text = reader.readtext(str(temp_path), detail=0)
        total_cents = find_total_cents(raw_text)
        return {
            "raw_text": raw_text,
            "parsed": {
                "total_cents": total_cents,
                "merchant_name": raw_text[0] if raw_text else None,
                "purchased_at": None,
            },
            "confidence": None,
            "parser_version": PARSER_VERSION,
        }
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@app.post("/upload")
async def legacy_upload(file: UploadFile) -> dict:
    result = await upload_for_ocr(file)
    return {"Ok": result["parsed"]["total_cents"]}
