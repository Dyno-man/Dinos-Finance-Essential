from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import cv2
import easyocr
from fastapi import FastAPI, HTTPException, UploadFile
from PIL import Image, ImageOps

from app.config import settings
from app.parser import PARSER_VERSION, find_total_cents


app = FastAPI(title="Receipt OCR Service")
reader: easyocr.Reader | None = None

# EasyOCR + OpenCV can crash with ``!ssize.empty()`` on ``cv2.resize`` when CRAFT
# returns degenerate crops (seen on some JPEGs / phone photos). Upscale small images,
# tighten bbox filters, and retry once on ``cv2.error``.
_MIN_EDGE_PX = 320
_MAX_EDGE_PX = 4000
_READTEXT_KW = dict(
    detail=0,
    min_size=36,
    bbox_min_size=10,
    bbox_min_score=0.28,
    text_threshold=0.65,
    low_text=0.38,
    link_threshold=0.35,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


def get_reader() -> easyocr.Reader:
    global reader
    if reader is None:
        reader = easyocr.Reader(["en"], gpu=False)
    return reader


def _decode_rgb(contents: bytes) -> Image.Image:
    with Image.open(BytesIO(contents)) as image:
        image.verify()
    im = Image.open(BytesIO(contents))
    im.load()
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def _resize_for_ocr(im: Image.Image) -> Image.Image:
    w, h = im.size
    if w < 2 or h < 2:
        raise ValueError("Image dimensions too small")
    min_edge, max_edge = min(w, h), max(w, h)
    if min_edge < _MIN_EDGE_PX:
        scale = _MIN_EDGE_PX / min_edge
        w2, h2 = max(2, int(w * scale)), max(2, int(h * scale))
        im = im.resize((w2, h2), Image.Resampling.LANCZOS)
        w, h = im.size
        max_edge = max(w, h)
    if max_edge > _MAX_EDGE_PX:
        scale = _MAX_EDGE_PX / max_edge
        w2, h2 = max(2, int(w * scale)), max(2, int(h * scale))
        im = im.resize((w2, h2), Image.Resampling.LANCZOS)
    return im


def _save_temp_png(im: Image.Image, temp_dir: Path) -> Path:
    with NamedTemporaryFile(delete=False, suffix=".png", dir=temp_dir) as png_file:
        out = Path(png_file.name)
    im.save(out, format="PNG")
    return out


def _readtext_paths(paths: list[Path], ocr_reader: easyocr.Reader | None = None) -> list[str]:
    last_exc: Exception | None = None
    active_reader = ocr_reader or get_reader()
    for path in paths:
        try:
            return active_reader.readtext(str(path), **_READTEXT_KW)
        except cv2.error as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    return []


def _run_easyocr(contents: bytes, temp_dir: Path) -> list[str]:
    im = _decode_rgb(contents)
    im = _resize_for_ocr(im)
    primary = _save_temp_png(im, temp_dir)
    paths: list[Path] = [primary]
    retry: Path | None = None
    try:
        w, h = im.size
        im_up = im.resize((max(2, int(w * 1.25)), max(2, int(h * 1.25))), Image.Resampling.LANCZOS)
        retry = _save_temp_png(im_up, temp_dir)
        paths.append(retry)
    except Exception:
        pass
    try:
        return _readtext_paths(paths)
    finally:
        primary.unlink(missing_ok=True)
        if retry is not None:
            retry.unlink(missing_ok=True)


@app.post("/ocr/upload")
async def upload_for_ocr(file: UploadFile) -> dict:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")

    temp_dir = Path(settings.temp_upload_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        raw_text = _run_easyocr(contents, temp_dir)
    except cv2.error:
        # Degenerate CRAFT crops; still accept upload with empty OCR text.
        raw_text = []
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc

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


@app.post("/upload")
async def legacy_upload(file: UploadFile) -> dict:
    result = await upload_for_ocr(file)
    return {"Ok": result["parsed"]["total_cents"]}
