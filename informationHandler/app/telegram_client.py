import httpx

from app.config import settings


class TelegramClient:
    def __init__(
        self,
        bot_token: str = settings.telegram_bot_token,
        enabled: bool = settings.telegram_reply_enabled,
    ) -> None:
        self.bot_token = bot_token
        self.enabled = enabled
        self.api_base_url = f"https://api.telegram.org/bot{bot_token}" if bot_token else ""
        self.file_base_url = f"https://api.telegram.org/file/bot{bot_token}" if bot_token else ""

    async def send_message(self, chat_id: str, message: str) -> None:
        if not self.enabled or not self.bot_token:
            return
        payload = {"chat_id": chat_id, "text": message}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{self.api_base_url}/sendMessage", json=payload)
            response.raise_for_status()

    async def download_file(self, file_id: str) -> bytes:
        if not self.bot_token:
            raise RuntimeError("Telegram bot token is not configured")
        async with httpx.AsyncClient(timeout=30) as client:
            file_response = await client.get(f"{self.api_base_url}/getFile", params={"file_id": file_id})
            file_response.raise_for_status()
            file_body = file_response.json()
            file_path = file_body.get("result", {}).get("file_path")
            if not file_path:
                raise RuntimeError("Telegram did not return a file path")
            download_response = await client.get(f"{self.file_base_url}/{file_path}")
            download_response.raise_for_status()
            return download_response.content


def get_telegram_client() -> TelegramClient:
    return TelegramClient()
