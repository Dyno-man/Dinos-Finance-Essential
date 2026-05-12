from datetime import timezone

from fastapi import Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_session
from app.models import Session as AuthSession
from app.models import Subscription, User, now_utc
from app.rate_limit import login_rate_limiter
from app.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    session_expires_at,
    verify_password,
)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr | None = None
    password: str = Field(min_length=12)


class LoginRequest(BaseModel):
    username: str
    password: str


def safe_user(user: User, plan: str = "basic") -> dict:
    return {"id": user.id, "username": user.username, "email": user.email, "role": user.role, "plan": plan}


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")


def create_session(session: DBSession, user: User, response: Response) -> None:
    token = new_session_token()
    auth_session = AuthSession(
        user_id=user.id,
        session_token_hash=hash_session_token(token),
        expires_at=session_expires_at(),
    )
    session.add(auth_session)
    session.flush()
    set_session_cookie(response, token)


def get_subscription_plan(session: DBSession, user_id: str) -> str:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == user_id))
    return subscription.plan_name if subscription is not None else "basic"


async def get_current_user(
    request: Request,
    session: DBSession = Depends(get_session),
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_hash = hash_session_token(token)
    auth_session = session.scalar(select(AuthSession).where(AuthSession.session_token_hash == token_hash))
    current_time = now_utc()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or auth_session.expires_at.astimezone(timezone.utc) <= current_time
    ):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = session.get(User, auth_session.user_id)
    if user is None or user.disabled_at is not None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def register_user(payload: RegisterRequest, response: Response, session: DBSession) -> dict:
    user = User(
        username=payload.username.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists") from exc
    create_session(session, user, response)
    session.commit()
    return {"user": safe_user(user)}


def login_user(payload: LoginRequest, response: Response, request: Request, session: DBSession) -> dict:
    identifier = payload.username.strip().lower()
    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_host}:{identifier}"
    login_rate_limiter.check(rate_limit_key)

    user = session.scalar(
        select(User).where(or_(User.username == payload.username.strip(), User.email == payload.username.strip()))
    )
    if user is None or user.disabled_at is not None or not verify_password(payload.password, user.password_hash):
        login_rate_limiter.record_failure(rate_limit_key)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    create_session(session, user, response)
    login_rate_limiter.clear(rate_limit_key)
    session.commit()
    return {"ok": True}


def logout_user(request: Request, response: Response, session: DBSession) -> dict:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        auth_session = session.scalar(
            select(AuthSession).where(AuthSession.session_token_hash == hash_session_token(token))
        )
        if auth_session is not None and auth_session.revoked_at is None:
            auth_session.revoked_at = now_utc()
            session.commit()
    clear_session_cookie(response)
    return {"ok": True}
