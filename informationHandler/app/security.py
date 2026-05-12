import hashlib
import hmac
import secrets
from datetime import timedelta

import bcrypt

from app.config import settings
from app.models import now_utc


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hmac.new(settings.session_secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def session_expires_at():
    return now_utc() + timedelta(days=settings.session_ttl_days)
