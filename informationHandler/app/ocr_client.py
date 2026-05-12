import httpx

from app.config import settings


class OCRClientError(RuntimeError):
    pass


class OCRClient:
    def __init__(self, base_url: str = settings.ocr_service_url) -> None:
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return True

    async def parse_image(self, filename: str, content_type: str | None, contents: bytes) -> dict:
        files = {"file": (filename, contents, content_type or "application/octet-stream")}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/ocr/upload", files=files)
        if response.status_code >= 400:
            raise OCRClientError(response.text)
        return response.json()


def get_ocr_client() -> OCRClient:
    return OCRClient()
