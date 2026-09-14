from datetime import datetime
from hashlib import md5
from pathlib import Path

import pytest

pytest.importorskip("aiosqlite")

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import async_sessionmaker

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.composition.container import create_container
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.auth import (
    AuthenticationSucceeded,
    BackendPasswordCredentials,
    LoginPolicyContext,
    SessionMetadata,
    SessionResolutionError,
    SessionResolved,
)
from gomazon_webasyst.contracts.enums import SessionResolutionErrorType
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactEmailRow, WaContactRow


@pytest.mark.asyncio
async def test_backend_password_auth_session_resolve_and_logout_end_to_end(tmp_path: Path):
    db_path = tmp_path / "auth.db"
    container = create_container(Settings(database_url=f"sqlite+aiosqlite:///{db_path}"))
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(container.engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(
            WaContactRow(
                id=42,
                name="Admin",
                login="admin",
                password=md5(b"secret").hexdigest(),
                is_user=1,
                create_datetime=datetime(2026, 1, 1, 12, 0, 0),
            )
        )
        session.add(WaContactEmailRow(contact_id=42, email="admin@example.com", sort=0))
        await session.commit()

    authenticated = await container.authenticate_backend_password(
        BackendPasswordCredentials(
            identifier="admin@example.com",
            password=SecretStr("secret"),
            login_context=LoginPolicyContext(enabled_schemes=("login", "email", "phone")),
            session_metadata=SessionMetadata(user_agent="pytest"),
        )
    )
    assert isinstance(authenticated, AuthenticationSucceeded)

    resolved = await container.resolve_backend_session(authenticated.session_key.session_id)
    assert isinstance(resolved, SessionResolved)
    assert resolved.subject.id == 42

    logout = await container.logout_backend_session(authenticated.session_key.session_id)
    assert logout.status.value == "revoked"

    after_logout = await container.resolve_backend_session(authenticated.session_key.session_id)
    assert isinstance(after_logout, SessionResolutionError)
    assert after_logout.type is SessionResolutionErrorType.NOT_FOUND

    await container.close()
