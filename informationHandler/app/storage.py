from pathlib import Path

from app.config import settings


class LocalReceiptStorage:
    def __init__(self, root: str = settings.receipt_storage_path) -> None:
        self.root = Path(root)

    def save_original(self, user_id: str, receipt_id: str, filename: str, contents: bytes) -> str:
        suffix = Path(filename or "receipt").suffix or ".img"
        receipt_dir = self.root / user_id / receipt_id
        receipt_dir.mkdir(parents=True, exist_ok=True)
        storage_path = receipt_dir / f"original{suffix}"
        storage_path.write_bytes(contents)
        return str(storage_path)


def get_storage() -> LocalReceiptStorage:
    return LocalReceiptStorage()
