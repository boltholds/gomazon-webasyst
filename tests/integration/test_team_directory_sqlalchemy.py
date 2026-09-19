from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.access_values import AppId, GroupId
from gomazon_webasyst.application.team_directory.vo.filters import (
    AllTeamUsers,
    TeamUsersInGroups,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamCurrentEventPresent,
    TeamDateTimeValue,
    TeamIntValue,
    TeamTextValue,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactCalendarRow,
    WaContactDataRow,
    WaContactEmailRow,
    WaContactEventRow,
    WaContactRightRow,
    WaContactRow,
    WaContactSettingRow,
    WaGroupRow,
    WaLoginLogRow,
    WaUserGroupRow,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.access import (
    SQLAlchemyTeamPrincipalGroupRightsReader,
    SQLAlchemyTeamUserAppAccessReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.current_events import (
    SQLAlchemyTeamCurrentEventReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.directory import (
    SQLAlchemyTeamDirectoryReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.memberships import (
    SQLAlchemyTeamMembershipReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.presence import (
    SQLAlchemyTeamPresenceReader,
)


NOW = datetime(2026, 9, 20, 12, 0, 0)


async def _stack():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sessions


async def _seed(sessions) -> None:
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=1,
                    name="Alice",
                    firstname="Alice",
                    is_user=1,
                    login="alice",
                    last_datetime=NOW - timedelta(seconds=30),
                    create_datetime=NOW - timedelta(days=10),
                    locale="en_US",
                    photo=100,
                ),
                WaContactRow(
                    id=2,
                    name="Bob",
                    firstname="Bob",
                    is_user=1,
                    login="bob",
                    last_datetime=NOW - timedelta(seconds=120),
                    create_datetime=NOW - timedelta(days=9),
                    locale="en_US",
                ),
                WaContactRow(
                    id=3,
                    name="Banned",
                    firstname="Banned",
                    is_user=-1,
                    login="banned",
                    create_datetime=NOW,
                    locale="en_US",
                ),
                WaContactRow(
                    id=4,
                    name="Contact",
                    firstname="Contact",
                    is_user=0,
                    login=None,
                    create_datetime=NOW,
                    locale="en_US",
                ),
                WaContactRow(
                    id=99,
                    name="Principal",
                    firstname="Principal",
                    is_user=1,
                    login="principal",
                    create_datetime=NOW,
                    locale="en_US",
                ),
            )
        )
        session.add_all(
            (
                WaGroupRow(
                    id=7,
                    name="Hidden",
                    cnt=1,
                    sort=2,
                    type="group",
                    description="Hidden group",
                ),
                WaGroupRow(
                    id=8,
                    name="Visible",
                    cnt=2,
                    sort=1,
                    type="location",
                    description=None,
                ),
            )
        )
        session.add_all(
            (
                WaUserGroupRow(contact_id=1, group_id=7),
                WaUserGroupRow(contact_id=2, group_id=8),
                WaUserGroupRow(contact_id=99, group_id=8),
            )
        )
        session.add_all(
            (
                WaContactEmailRow(
                    contact_id=1,
                    email="second@example.test",
                    sort=1,
                ),
                WaContactEmailRow(
                    contact_id=1,
                    email="first@example.test",
                    sort=0,
                ),
                WaContactDataRow(
                    contact_id=1,
                    field="phone",
                    ext="work",
                    value="+100",
                    sort=1,
                    status=None,
                ),
                WaContactDataRow(
                    contact_id=1,
                    field="phone",
                    ext="mobile",
                    value="+200",
                    sort=0,
                    status="confirmed",
                ),
            )
        )
        session.add_all(
            (
                # Alice is global admin: non-webasyst app access becomes unlimited.
                WaContactRightRow(
                    group_id=-1,
                    app_id="webasyst",
                    name="backend",
                    value=1,
                ),
                # Bob has limited personal CRM and full CRM through group 8.
                WaContactRightRow(
                    group_id=-2,
                    app_id="crm",
                    name="backend",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=8,
                    app_id="crm",
                    name="backend",
                    value=2,
                ),
                # Principal has limited Team app access.
                WaContactRightRow(
                    group_id=-99,
                    app_id="team",
                    name="backend",
                    value=1,
                ),
                # Explicit negative right for group 7.
                WaContactRightRow(
                    group_id=-99,
                    app_id="team",
                    name="manage_users_in_group.7",
                    value=-1,
                ),
                # Fallback allows other groups.
                WaContactRightRow(
                    group_id=-99,
                    app_id="team",
                    name="manage_users_in_group.all",
                    value=1,
                ),
            )
        )
        session.add(
            WaLoginLogRow(
                contact_id=1,
                datetime_in=NOW - timedelta(hours=1),
                datetime_out=None,
                ip="127.0.0.1",
            )
        )
        session.add(
            WaContactSettingRow(
                contact_id=1,
                app_id="webasyst",
                name="idle_since",
                value=(NOW - timedelta(minutes=5)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            )
        )
        session.add(
            WaContactCalendarRow(
                id=5,
                name="Status",
                bg_color="#ffffff",
                font_color="#000000",
                status_bg_color="#112233",
                status_font_color="#eeeeee",
                icon="status",
                sort=0,
                is_limited=0,
                default_status=None,
            )
        )
        session.add_all(
            (
                WaContactEventRow(
                    id=10,
                    uid="timed",
                    create_datetime=NOW - timedelta(days=1),
                    update_datetime=NOW - timedelta(hours=1),
                    contact_id=1,
                    calendar_id=5,
                    summary="Timed",
                    description=None,
                    location=None,
                    start=NOW - timedelta(minutes=5),
                    end=NOW + timedelta(minutes=5),
                    is_allday=0,
                    is_status=1,
                    sequence=0,
                ),
                WaContactEventRow(
                    id=11,
                    uid="all-day",
                    create_datetime=NOW - timedelta(days=1),
                    update_datetime=NOW,
                    contact_id=1,
                    calendar_id=5,
                    summary="All day wins",
                    description="desc",
                    location="Here",
                    start=NOW.replace(hour=0, minute=0),
                    end=NOW.replace(hour=23, minute=59),
                    is_allday=1,
                    is_status=1,
                    sequence=1,
                ),
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_team_directory_sqlalchemy_vertical_reads_legacy_shape() -> None:
    engine, sessions = await _stack()
    try:
        await _seed(sessions)

        directory = SQLAlchemyTeamDirectoryReader(sessions)
        memberships = SQLAlchemyTeamMembershipReader(sessions)
        access = SQLAlchemyTeamUserAppAccessReader(sessions)
        group_rights = SQLAlchemyTeamPrincipalGroupRightsReader(sessions)
        presence = SQLAlchemyTeamPresenceReader(sessions)
        events = SQLAlchemyTeamCurrentEventReader(sessions)

        users = (await directory.list_users(AllTeamUsers())).users
        assert tuple(user.id for user in users) == (1, 2, 99)
        alice = users[0]
        assert tuple(email.value for email in alice.emails) == (
            "first@example.test",
            "second@example.test",
        )
        assert tuple(phone.value for phone in alice.phones) == (
            "+200",
            "+100",
        )
        assert isinstance(alice.phones[0].status, TeamTextValue)
        assert alice.phones[0].status.value == "confirmed"

        group_filtered = (
            await directory.list_users(
                TeamUsersInGroups((GroupId(7),))
            )
        ).users
        assert tuple(user.id for user in group_filtered) == (1,)

        groups = (await directory.list_groups()).groups
        assert tuple(group.id for group in groups) == (
            GroupId(8),
            GroupId(7),
        )

        membership_snapshot = await memberships.for_users((1, 2, 99))
        assert membership_snapshot.memberships[0].group_ids == (
            GroupId(7),
        )
        assert membership_snapshot.memberships[1].group_ids == (
            GroupId(8),
        )

        access_snapshot = await access.read(
            (1, 2),
            (AppId("crm"),),
        )
        values = {
            item.contact_id: item.value
            for item in access_snapshot.accesses
        }
        assert values[1] > 2
        assert values[2] == 2

        rights = await group_rights.read(
            99,
            (GroupId(7), GroupId(8)),
        )
        assert rights.is_team_admin is False
        assert tuple(
            (item.group_id, item.value) for item in rights.rights
        ) == ((GroupId(7), -1),)
        assert isinstance(rights.all_groups_fallback, TeamIntValue)
        assert rights.all_groups_fallback.value == 1

        presence_snapshot = await presence.read((1, 2))
        alice_presence = presence_snapshot.entries[0]
        bob_presence = presence_snapshot.entries[1]
        assert alice_presence.has_open_login is True
        assert isinstance(alice_presence.idle_since, TeamDateTimeValue)
        assert bob_presence.has_open_login is False

        current = await events.current_for_users((1, 2), NOW)
        assert isinstance(current.entries[0].state, TeamCurrentEventPresent)
        assert current.entries[0].state.event.id == 11
        assert current.entries[0].state.event.summary == "All day wins"
        assert current.entries[0].state.event.calendar_name == "Status"
        assert type(current.entries[1].state).__name__ == (
            "TeamCurrentEventMissing"
        )
    finally:
        await engine.dispose()
