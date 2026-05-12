from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User


def get_or_create_dev_user(session: Session) -> User:
    user = session.scalar(select(User).where(User.username == settings.dev_username))
    if user is not None:
        return user

    user = User(
        username=settings.dev_username,
        email=settings.dev_email,
        password_hash=settings.dev_password_hash,
        role="user",
    )
    session.add(user)
    session.flush()
    return user
