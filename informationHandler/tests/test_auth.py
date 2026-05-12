import asyncio
from http.cookies import SimpleCookie

import pytest
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import (
    LoginRequest,
    RegisterRequest,
    get_current_user,
    login_user,
    logout_user,
    register_user,
)
from app.config import settings
from app.main import list_receipts
from app.models import Base, Receipt, Session as AuthSession, User
from app.rate_limit import login_rate_limiter
from app.security import hash_password, verify_password


def make_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def make_request(cookie_value: str | None = None, host: str = "127.0.0.1") -> Request:
    headers = []
    if cookie_value is not None:
        headers.append((b"cookie", f"{settings.session_cookie_name}={cookie_value}".encode("latin-1")))
    return Request({"type": "http", "headers": headers, "client": (host, 12345)})


def cookie_from_response(response: Response) -> str:
    cookie = SimpleCookie()
    for header, value in response.raw_headers:
        if header == b"set-cookie":
            cookie.load(value.decode("latin-1"))
    return cookie[settings.session_cookie_name].value


def test_register_hashes_password_and_sets_cookie() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        response = Response()
        body = register_user(
            RegisterRequest(username="grant", email="grant@example.com", password="long-password"),
            response,
            session,
        )

        assert body["user"]["username"] == "grant"
        assert cookie_from_response(response)

        user = session.scalar(select(User).where(User.username == "grant"))
        assert user is not None
        assert user.password_hash != "long-password"
        assert verify_password("long-password", user.password_hash)
        assert session.scalar(select(AuthSession).where(AuthSession.user_id == user.id)) is not None


def test_duplicate_username_is_rejected() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        register_user(
            RegisterRequest(username="grant", email="grant@example.com", password="long-password"),
            Response(),
            session,
        )
        with pytest.raises(Exception) as exc:
            register_user(
                RegisterRequest(username="grant", email="other@example.com", password="long-password"),
                Response(),
                session,
            )
        assert getattr(exc.value, "status_code", None) == 409


def test_login_me_and_logout_flow() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = User(
            username="grant",
            email="grant@example.com",
            password_hash=hash_password("long-password"),
        )
        session.add(user)
        session.commit()

        with pytest.raises(Exception) as exc:
            login_user(
                LoginRequest(username="grant", password="wrong-password"),
                Response(),
                make_request(host="10.0.0.1"),
                session,
            )
        assert getattr(exc.value, "status_code", None) == 401

        response = Response()
        assert login_user(
            LoginRequest(username="grant@example.com", password="long-password"),
            response,
            make_request(host="10.0.0.2"),
            session,
        ) == {"ok": True}

        token = cookie_from_response(response)
        current_user = asyncio.run(get_current_user(make_request(token), session))
        assert current_user.username == "grant"

        logout_response = Response()
        assert logout_user(make_request(token), logout_response, session) == {"ok": True}
        with pytest.raises(Exception) as logged_out:
            asyncio.run(get_current_user(make_request(token), session))
        assert getattr(logged_out.value, "status_code", None) == 401


def test_receipts_are_scoped_to_current_user() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        grant = User(username="grant", email="grant@example.com", password_hash="hash")
        other = User(username="other", email="other@example.com", password_hash="hash")
        session.add_all([grant, other])
        session.flush()
        session.add(Receipt(user_id=grant.id, source="web", status="pending_review", merchant_name="Mine"))
        session.add(Receipt(user_id=other.id, source="web", status="pending_review", merchant_name="Theirs"))
        session.commit()

        body = asyncio.run(list_receipts(grant, session))
        assert len(body["receipts"]) == 1
        assert body["receipts"][0]["merchant_name"] == "Mine"


def test_me_requires_authentication() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        with pytest.raises(Exception) as exc:
            asyncio.run(get_current_user(make_request(), session))
        assert getattr(exc.value, "status_code", None) == 401


def test_login_rate_limiter_blocks_repeated_failures() -> None:
    session_factory = make_session_factory()
    with session_factory() as session:
        user = User(username="grant", email="grant@example.com", password_hash=hash_password("long-password"))
        session.add(user)
        session.commit()
        key = "10.0.0.3:grant"
        login_rate_limiter.clear(key)

        for _ in range(settings.login_rate_limit_attempts):
            with pytest.raises(Exception):
                login_user(LoginRequest(username="grant", password="bad-password"), Response(), make_request(host="10.0.0.3"), session)

        with pytest.raises(Exception) as exc:
            login_user(LoginRequest(username="grant", password="bad-password"), Response(), make_request(host="10.0.0.3"), session)
        assert getattr(exc.value, "status_code", None) == 429
        login_rate_limiter.clear(key)
