from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException

from app.config import settings


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = monotonic()
        attempts = self._attempts[key]
        while attempts and now - attempts[0] > settings.login_rate_limit_window_seconds:
            attempts.popleft()
        if len(attempts) >= settings.login_rate_limit_attempts:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    def record_failure(self, key: str) -> None:
        self._attempts[key].append(monotonic())

    def clear(self, key: str) -> None:
        self._attempts.pop(key, None)


login_rate_limiter = LoginRateLimiter()
