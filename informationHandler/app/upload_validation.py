import hashlib
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import settings

SUPPORTED_IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def upload_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def validate_image_bytes(contents: bytes) -> tuple[str, str]:
    if not contents:
        raise upload_error(400, "empty_file", "Choose a receipt image before uploading.")
    if len(contents) > settings.max_upload_bytes:
        raise upload_error(
            413,
            "file_too_large",
            f"Receipt images must be {settings.max_upload_mb} MB or smaller.",
        )

    try:
        with Image.open(BytesIO(contents)) as image:
            image.verify()
            image_format = image.format
    except Exception as exc:
        raise upload_error(400, "invalid_file_type", "Upload a valid JPG, PNG, or WebP receipt image.") from exc

    mime_type = SUPPORTED_IMAGE_FORMATS.get(str(image_format).upper())
    if mime_type is None:
        raise upload_error(400, "invalid_file_type", "Upload a JPG, PNG, or WebP receipt image.")

    return hashlib.sha256(contents).hexdigest(), mime_type


async def read_valid_image(file: UploadFile) -> tuple[bytes, str, str]:
    contents = await file.read()
    digest, mime_type = validate_image_bytes(contents)
    return contents, digest, mime_type
