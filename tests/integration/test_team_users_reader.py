from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.contracts.enums import TeamUserOnlineStatus
from gomazon_webasyst.contracts.team import (
    TeamDateTimePresent,
    TeamEventPresent,
    TeamIntegerPresent,
    TeamTextMissing,
    TeamTextPresent,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRow,
    WaUserGroupRow,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.users import (
    SQLAlchemyTeamUserReader,
)


_EXTRA_DDL = (
    "CREATE TABLE wa_app_settings (app_id TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(app_id, name))",
    "CREATE TABLE wa_contact_settings (contact_id INTEGER NOT NULL, app_id TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(contact_id, app_id, name))",
    "CREATE TABLE wa_login_log (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, datetime_in DATETIME NOT NULL, datetime_out DATETIME, ip TEXT)",
    "CREATE TABLE wa_contact_calendars (id INTEGER PRIMARY KEY, name TEXT NOT NULL, bg_color TEXT, font_color TEXT, status_bg_color TEXT, status_font_color TEXT, icon TEXT)",
    "CREATE TABLE wa_contact_events (id INTEGER PRIMARY KEY, uid TEXT, create_datetime DATETIME NOT NULL, update_datetime DATETIME NOT NULL, contact_id INTEGER NOT NULL, calendar_id INTEGER NOT NULL, summary TEXT NOT NULL, description TEXT, location TEXT, start DATETIME NOT NULL, end DATETIME NOT NULL, is_allday INTEGER NOT NULL, is_status INTEGER NOT NULL, sequence INTEGER NOT NULL)",
)


async def _database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        for ddl in _EXTRA_DDL:
            await connection.exec_driver_sql(ddl)
    return engine


def _reader(sessions):
    return SQLAlchemyTeamUserReader(
        sessions,
        server_timezone=timezone.utc,
        clock=lambda: datetime(2026, 9, 20, 12, 0, 0),
    )


@pytest.mark.asyncio
async def test_team_user_reader_uses_users_collection_without_group_filter() -> None:
    engine = await _database()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=1,
                    name="Zulu Stored",
                    firstname="Alice",
                    lastname="Zulu",
                    login="alice",
                    is_user=1,
                    last_datetime=datetime(2026, 9, 20, 11, 58, 0),
                    birth_day=10,
                    birth_month=5,
                    photo=7,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
                WaContactRow(
                    id=2,
                    name="No Login",
                    firstname="No",
                    login=None,
                    is_user=1,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
                WaContactRow(
                    id=3,
                    name="Banned",
                    login="banned",
                    is_user=-1,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
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
                    value="1234567",
                    sort=0,
                    status=None,
                ),
                WaUserGroupRow(
                    contact_id=1,
                    group_id=4,
                    datetime=datetime(2026, 9, 20, 8, 0, 0),
                ),
            )
        )
        await session.execute(
            text(
                "INSERT INTO wa_app_settings(app_id,name,value) "
                "VALUES ('webasyst','user_name_display','lastname,firstname')"
            )
        )
        await session.execute(
            text(
                "INSERT INTO wa_login_log(id,contact_id,datetime_in,datetime_out) "
                "VALUES (1,1,'2026-09-20 10:00:00',NULL)"
            )
        )
        await session.execute(
            text(
                "INSERT INTO wa_contact_settings(contact_id,app_id,name,value) "
                "VALUES (1,'webasyst','idle_since','2026-09-20 11:55:00')"
            )
        )
        await session.execute(
            text(
                "INSERT INTO wa_contact_calendars(id,name,status_bg_color,status_font_color) "
                "VALUES (1,'Work','#111111','#ffffff')"
            )
        )
        await session.execute(
            text(
                "INSERT INTO wa_contact_events("
                "id,uid,create_datetime,update_datetime,contact_id,calendar_id,"
                "summary,start,end,is_allday,is_status,sequence"
                ") VALUES ("
                "1,'evt','2026-09-20 09:00:00','2026-09-20 09:00:00',"
                "1,1,'Busy','2026-09-20 11:00:00','2026-09-20 13:00:00',0,1,0"
                ")"
            )
        )
        await session.commit()

    users = await _reader(sessions).list_candidates(())

    assert len(users) == 1
    user = users[0]
    assert user.id == 1
    assert user.name == "Zulu Alice"
    assert user.email == ("first@example.test", "second@example.test")
    assert user.group_ids == (4,)
    assert isinstance(user.login, TeamTextPresent)
    assert user.login.value == "alice"
    assert isinstance(user.last_datetime, TeamDateTimePresent)
    assert isinstance(user.birth_day, TeamIntegerPresent)
    assert user.phone[0].value == "1234567"
    assert isinstance(user.phone[0].ext, TeamTextPresent)
    assert isinstance(user.phone[0].status, TeamTextMissing)
    assert user.online_status is TeamUserOnlineStatus.IDLE
    assert isinstance(user.event, TeamEventPresent)
    assert user.event.value["summary"] == "Busy"
    assert user.create_datetime == datetime(2026, 9, 20, 9, 0, 0)

    await engine.dispose()


@pytest.mark.asyncio
async def test_group_filter_switches_to_group_collection_semantics() -> None:
    engine = await _database()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=1,
                    name="User One",
                    login=None,
                    is_user=1,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
                WaContactRow(
                    id=2,
                    name="Banned",
                    login="banned",
                    is_user=-1,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
                WaContactRow(
                    id=3,
                    name="Other Group",
                    login="other",
                    is_user=1,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
            )
        )
        session.add_all(
            (
                WaUserGroupRow(contact_id=1, group_id=10),
                WaUserGroupRow(contact_id=2, group_id=10),
                WaUserGroupRow(contact_id=3, group_id=11),
            )
        )
        await session.commit()

    users = await _reader(sessions).list_candidates((10,))

    assert [user.id for user in users] == [1]
    assert isinstance(users[0].login, TeamTextMissing)

    await engine.dispose()


@pytest.mark.asyncio
async def test_absent_name_setting_falls_back_to_stored_contact_name_and_sorts_it() -> None:
    engine = await _database()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=1,
                    name="Zulu",
                    firstname="A",
                    login="one",
                    is_user=1,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
                WaContactRow(
                    id=2,
                    name="Alpha",
                    firstname="Z",
                    login="two",
                    is_user=1,
                    create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                ),
            )
        )
        await session.commit()

    users = await _reader(sessions).list_candidates(())

    assert [user.name for user in users] == ["Alpha", "Zulu"]

    await engine.dispose()
