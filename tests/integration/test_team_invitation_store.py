from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.contracts.enums import TeamInvitationRejectReason
from gomazon_webasyst.contracts.team import TeamTextMissing, TeamTextPresent
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationCodeRequest,
    TeamInvitationContactConflict,
    TeamInvitationEmailLinkRequest,
    TeamInvitationPhoneLinkRequest,
    TeamInvitationPrepared,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRow,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.invitation import (
    SQLAlchemyTeamInvitationStore,
)


NOW = datetime(2026, 9, 20, 12, 0, 0)


async def _store(token_factory=None):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.exec_driver_sql(
            "CREATE TABLE wa_app_tokens ("
            "contact_id INTEGER, app_id TEXT NOT NULL, type TEXT NOT NULL, "
            "create_datetime DATETIME NOT NULL, expire_datetime DATETIME, "
            "token TEXT PRIMARY KEY NOT NULL, data TEXT)"
        )
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
    tokens = iter(f"token-{i:026d}"[:32] for i in range(100))
    return engine, sessions, SQLAlchemyTeamInvitationStore(
        sessions,
        clock=lambda: NOW,
        token_factory=token_factory or (lambda: next(tokens)),
    )


@pytest.mark.asyncio
async def test_link_reuses_non_user_and_persists_filtered_groups() -> None:
    engine, sessions, store = await _store()
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=7,
                    name="Existing",
                    is_user=0,
                    locale="ru_RU",
                    create_datetime=NOW,
                ),
                WaContactEmailRow(
                    contact_id=7,
                    email="person@example.test",
                    sort=0,
                ),
            )
        )
        await session.commit()

    result = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationEmailLinkRequest(
            email="person@example.test",
            requested_groups=("2", "bad"),
            integer_group_ids=(2,),
        ),
        manageable_group_ids=(2,),
    )
    assert isinstance(result, TeamInvitationPrepared)
    assert result.contact_id == 7
    assert result.recipient_locale == "ru_RU"

    async with sessions() as session:
        row = (
            await session.execute(
                text(
                    "SELECT type, expire_datetime, data "
                    "FROM wa_app_tokens WHERE token=:token"
                ),
                {"token": result.token},
            )
        ).mappings().one()
        assert row["type"] == "user_invite"
        assert datetime.fromisoformat(row["expire_datetime"]) == NOW + timedelta(days=3)
        assert row["data"] == '{"full_access":false,"groups":[2]}'
    await engine.dispose()


@pytest.mark.asyncio
async def test_link_conflicts_and_code_does_not_reuse_existing_contact() -> None:
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
                    name="Reuse Candidate",
                    is_user=0,
                    create_datetime=NOW,
                ),
                WaContactEmailRow(
                    contact_id=7,
                    email="user@example.test",
                    sort=0,
                ),
                WaContactEmailRow(
                    contact_id=8,
                    email="same@example.test",
                    sort=0,
                ),
            )
        )
        await session.commit()

    conflict = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationEmailLinkRequest(email="user@example.test"),
        manageable_group_ids=(),
    )
    assert isinstance(conflict, TeamInvitationContactConflict)
    assert conflict.reason is TeamInvitationRejectReason.USER_IN_TEAM

    code = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationCodeRequest(
            email=TeamTextPresent(value="same@example.test"),
            phone=TeamTextMissing(),
        ),
        manageable_group_ids=(),
    )
    assert isinstance(code, TeamInvitationPrepared)
    assert code.contact_id != 8

    async with sessions() as session:
        token_type = (
            await session.execute(
                text("SELECT type FROM wa_app_tokens WHERE token=:token"),
                {"token": code.token},
            )
        ).scalar_one()
        assert token_type == "waid_invite"
    await engine.dispose()


@pytest.mark.asyncio
async def test_phone_lookup_uses_legacy_one_pass_cleaning() -> None:
    engine, sessions, store = await _store()
    async with sessions() as session:
        session.add(
            WaContactRow(
                id=9,
                name="Phone",
                is_user=0,
                create_datetime=NOW,
            )
        )
        session.add(
            WaContactDataRow(
                contact_id=9,
                field="phone",
                ext="",
                value="12 3",
                sort=0,
            )
        )
        await session.commit()

    result = await store.prepare(
        actor_contact_id=42,
        request=TeamInvitationPhoneLinkRequest(phone="+1 2 3"),
        manageable_group_ids=(),
    )

    assert isinstance(result, TeamInvitationPrepared)
    assert result.contact_id == 9
    await engine.dispose()


@pytest.mark.asyncio
async def test_token_collision_keeps_previously_committed_contact() -> None:
    token = "x" * 32
    engine, sessions, store = await _store(token_factory=lambda: token)
    async with sessions() as session:
        await session.execute(
            text(
                "INSERT INTO wa_app_tokens("
                "contact_id,app_id,type,create_datetime,"
                "expire_datetime,token,data"
                ") VALUES("
                "42,'team','user_invite',:created,:expires,:token,'{}'"
                ")"
            ),
            {
                "created": NOW,
                "expires": NOW + timedelta(days=3),
                "token": token,
            },
        )
        await session.commit()

    with pytest.raises(IntegrityError):
        await store.prepare(
            actor_contact_id=42,
            request=TeamInvitationEmailLinkRequest(
                email="new@example.test"
            ),
            manageable_group_ids=(),
        )

    async with sessions() as session:
        created = tuple(
            (
                await session.execute(
                    select(WaContactRow).where(
                        WaContactRow.create_method == "invite"
                    )
                )
            ).scalars()
        )
        assert len(created) == 1
        assert created[0].name == "new"
        assert created[0].create_app_id == "team"
        assert created[0].create_contact_id == 42
    await engine.dispose()
