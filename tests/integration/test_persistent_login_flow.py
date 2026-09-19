from datetime import datetime
from hashlib import md5
from pathlib import Path

import pytest

pytest.importorskip("aiosqlite")

from pydantic import SecretStr
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.composition.container import create_container_with_application_catalog
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.auth import (
    AuthenticationSucceeded,
    BackendPasswordCredentials,
    LoginPolicyContext,
    SessionMetadata,
)
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    PersistentCredentialIssued,
    PersistentLoginRejected,
    PersistentLoginRequest,
    PersistentLoginRestored,
    RefreshPersistentCredential,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow


@pytest.mark.asyncio
async def test_issue_restore_and_credential_invalidation_end_to_end(tmp_path: Path):
    db_path = tmp_path / "persistent-login.db"
    container = create_container_with_application_catalog(
        Settings(database_url=f"sqlite+aiosqlite:///{db_path}"),
        installed_application_catalog=InMemoryInstalledApplicationCatalog(()),
    )
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
        await session.commit()

    authenticated = await container.authenticate_backend_password(
        BackendPasswordCredentials(
            identifier="admin",
            password=SecretStr("secret"),
            login_context=LoginPolicyContext(enabled_schemes=("login",)),
            session_metadata=SessionMetadata(user_agent="password-login"),
        )
    )
    assert isinstance(authenticated, AuthenticationSucceeded)

    issued = await container.issue_persistent_credential(authenticated.subject)
    assert isinstance(issued, PersistentCredentialIssued)
    legacy_credential = issued.credential
    assert isinstance(legacy_credential, PersistentCredential)

    await container.logout_backend_session(authenticated.session_key.session_id)

    restored = await container.restore_backend_session_from_persistent_credential(
        PersistentLoginRequest(
            credential=legacy_credential,
            session_metadata=SessionMetadata(user_agent="cookie-restore"),
        )
    )
    assert isinstance(restored, PersistentLoginRestored)
    assert restored.subject.id == 42
    assert restored.session_key != authenticated.session_key
    assert isinstance(restored.credential_disposition, RefreshPersistentCredential)
    assert restored.credential_disposition.credential == legacy_credential

    async with sessions() as session:
        await session.execute(
            update(WaContactRow)
            .where(WaContactRow.id == 42)
            .values(
                login="renamed-admin",
                password=md5(b"changed-secret").hexdigest(),
            )
        )
        await session.commit()

    rejected = await container.restore_backend_session_from_persistent_credential(
        PersistentLoginRequest(
            credential=legacy_credential,
            session_metadata=SessionMetadata(user_agent="stale-cookie"),
        )
    )
    assert isinstance(rejected, PersistentLoginRejected)
    assert isinstance(rejected.credential_disposition, ClearPersistentCredential)

    await container.close()
