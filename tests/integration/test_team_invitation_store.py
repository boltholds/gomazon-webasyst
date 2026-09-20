from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.contracts.enums import (
    TeamInvitationMode,
    TeamInvitationRejectReason,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationContactConflict,
    TeamInvitationPrepared,
    TeamInvitationRequest,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaAppTokenRow,
    WaContactEmailRow,
    WaContactRow,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.invitation import (
    SQLAlchemyTeamInvitationStore,
)


NOW = datetime(2026, 9, 20, 12, 0, 0)


async def _store():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(
            WaContactRow(
                id=42,
                name="Actor",
                login="actor",
                is_user=1,
                locale="en_US",
                create_datetime=NOW,
            )
        )
        await session.commit()
    tokens = iter(
        f"token-{index:026d}"[:32]
        for index in range(100)
    )
    return (
        engine,
        sessions,
        SQLAlchemyTeamInvitationStore(
            sessions,
            clock=lambda: NOW,
            token_factory=lambda: next(tokens),
        ),
    )


@pytest.mark.asyncio
async def test_link_email_reuses_existing_non_user_and_creates_user_invite_token() -> None:
    engine, sessions, store = await _store()
    async with sessions() as session:
        contact = WaContactRow(
            id=7,
            name="Existing",
            is_user=0,
            locale="ru_RU",
            create_datetime=NOW,
        )
        session.add(contact)
        session.add(
            WaContactEmailRow(
                contact_id=7,
                email="person@example.test",
                sort=0,
            )
        )
        await session.commit()

    result = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="person@example.test",
            group_ids=(2, 3),
        ),
        manageable_group_ids=(3,),
    )

    assert isinstance(result, TeamInvitationPrepared)
    assert result.contact_id == 7
    async with sessions() as session:
        token = await session.get(WaAppTokenRow, result.token)
        assert token.type == "user_invite"
        assert token.contact_id == 7
        assert token.expire_datetime == NOW + timedelta(days=3)
        assert token.data == '{"full_access":false,"groups":[3]}'
    await engine.dispose()


@pytest.mark.asyncio
async def test_link_existing_user_and_banned_user_are_typed_conflicts() -> None:
    engine, sessions, store = await _store()
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=7,
                    name="User",
                    is_user=1,
                    create_datetime=NOW,
                ),
                WaContactRow(
                    id=8,
                    name="Banned",
                    is_user=-1,
                    login="banned",
                    create_datetime=NOW,
                ),
                WaContactEmailRow(
                    contact_id=7,
                    email="user@example.test",
                    sort=0,
                ),
                WaContactEmailRow(
                    contact_id=8,
                    email="banned@example.test",
                    sort=0,
                ),
            )
        )
        await session.commit()

    user = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="user@example.test",
        ),
        manageable_group_ids=(),
    )
    banned = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="banned@example.test",
        ),
        manageable_group_ids=(),
    )

    assert isinstance(user, TeamInvitationContactConflict)
    assert user.reason is TeamInvitationRejectReason.USER_IN_TEAM
    assert isinstance(banned, TeamInvitationContactConflict)
    assert banned.reason is TeamInvitationRejectReason.CONTACT_BANNED
    await engine.dispose()


@pytest.mark.asyncio
async def test_code_flow_creates_new_contact_without_lookup_and_waid_token() -> None:
    engine, sessions, store = await _store()
    async with sessions() as session:
        session.add(
            WaContactRow(
                id=7,
                name="Existing",
                is_user=0,
                create_datetime=NOW,
            )
        )
        session.add(
            WaContactEmailRow(
                contact_id=7,
                email="same@example.test",
                sort=0,
            )
        )
        await session.commit()

    result = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.CODE,
            email="same@example.test",
        ),
        manageable_group_ids=(),
    )

    assert isinstance(result, TeamInvitationPrepared)
    assert result.contact_id != 7
    async with sessions() as session:
        token = await session.get(WaAppTokenRow, result.token)
        assert token.type == "waid_invite"
        contacts = tuple(
            (
                await session.execute(
                    select(WaContactRow).order_by(WaContactRow.id)
                )
            ).scalars()
        )
        assert [contact.id for contact in contacts] == [7, 42, result.contact_id]
    await engine.dispose()
