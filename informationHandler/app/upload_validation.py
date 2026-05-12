import hashlib
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import settings


async def read_valid_image(file: UploadFile) -> tuple[bytes, str]:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")

    try:
        with Image.open(BytesIO(contents)) as image:
            image.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc

    return contents, hashlib.sha256(contents).hexdigest()
