from datetime import datetime

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gomazon_webasyst.contracts.auth import IdentityKey, IdentityLookupPlan, IdentityResolved, IdentityResolutionError
from gomazon_webasyst.infrastructure.auth.identity_directory import create_sqlalchemy_identity_directory
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRow,
)


async def make_directory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory, create_sqlalchemy_identity_directory(session_factory)


def contact(contact_id: int, *, login: str, is_user: int = 1, password: str = "hash"):
    return WaContactRow(
        id=contact_id,
        name=login,
        login=login,
        password=password,
        is_user=is_user,
        create_datetime=datetime(2026, 1, contact_id),
    )


@pytest.mark.asyncio
async def test_login_resolver_requires_backend_user_and_non_empty_password():
    engine, factory, directory = await make_directory()
    async with factory() as session:
        session.add_all(
            [
                contact(1, login="disabled", is_user=0),
                contact(2, login="nopass", password=""),
                contact(3, login="admin"),
            ]
        )
        await session.commit()

    result = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="login", value="admin"),))
    )
    disabled = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="login", value="disabled"),))
    )
    nopass = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="login", value="nopass"),))
    )

    assert isinstance(result, IdentityResolved)
    assert result.identity.id == 3
    assert isinstance(disabled, IdentityResolutionError)
    assert isinstance(nopass, IdentityResolutionError)
    await engine.dispose()


@pytest.mark.asyncio
async def test_email_resolver_uses_primary_email_and_first_contact_id():
    engine, factory, directory = await make_directory()
    async with factory() as session:
        session.add_all([contact(2, login="second"), contact(1, login="first")])
        session.add_all(
            [
                WaContactEmailRow(contact_id=2, email="same@example.com", sort=0),
                WaContactEmailRow(contact_id=1, email="same@example.com", sort=0),
                WaContactEmailRow(contact_id=1, email="secondary@example.com", sort=1),
            ]
        )
        await session.commit()

    result = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="email", value="same@example.com"),))
    )
    secondary = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="email", value="secondary@example.com"),))
    )

    assert isinstance(result, IdentityResolved)
    assert result.identity.id == 1
    assert isinstance(secondary, IdentityResolutionError)
    await engine.dispose()


@pytest.mark.asyncio
async def test_phone_resolver_cleans_legacy_phone_and_uses_primary_row():
    engine, factory, directory = await make_directory()
    async with factory() as session:
        session.add(contact(1, login="phone-user"))
        session.add_all(
            [
                WaContactDataRow(contact_id=1, field="phone", value="31201234567", sort=0),
                WaContactDataRow(contact_id=1, field="phone", value="999", sort=1),
            ]
        )
        await session.commit()

    result = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="phone", value="+31 (20) 123 45 67"),))
    )

    assert isinstance(result, IdentityResolved)
    assert result.identity.id == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_phone_resolver_retries_with_configured_prefix_transformation():
    from gomazon_webasyst.compatibility.webasyst.auth.phone import LegacyPhonePrefixPolicy

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    directory = create_sqlalchemy_identity_directory(
        factory,
        phone_candidates=LegacyPhonePrefixPolicy(input_code="8", output_code="7").candidates,
    )
    async with factory() as session:
        session.add(contact(1, login="phone-transform-user"))
        session.add(WaContactDataRow(contact_id=1, field="phone", value="712345", sort=0))
        await session.commit()

    result = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="phone", value="812345"),))
    )

    assert isinstance(result, IdentityResolved)
    assert result.identity.id == 1
    await engine.dispose()
