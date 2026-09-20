from datetime import datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaApiTokenRow,
    WaContactEmailRow,
    WaContactRightRow,
    WaContactRow,
    WaUserGroupRow,
)
from gomazon_webasyst.main import create_app_with_settings


TOKEN = "u" * 32

_EXTRA_DDL = (
    "CREATE TABLE wa_app_settings (app_id TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(app_id, name))",
    "CREATE TABLE wa_contact_settings (contact_id INTEGER NOT NULL, app_id TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(contact_id, app_id, name))",
    "CREATE TABLE wa_login_log (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, datetime_in DATETIME NOT NULL, datetime_out DATETIME, ip TEXT)",
    "CREATE TABLE wa_contact_calendars (id INTEGER PRIMARY KEY, name TEXT NOT NULL, bg_color TEXT, font_color TEXT, status_bg_color TEXT, status_font_color TEXT, icon TEXT)",
    "CREATE TABLE wa_contact_events (id INTEGER PRIMARY KEY, uid TEXT, create_datetime DATETIME NOT NULL, update_datetime DATETIME NOT NULL, contact_id INTEGER NOT NULL, calendar_id INTEGER NOT NULL, summary TEXT NOT NULL, description TEXT, location TEXT, start DATETIME NOT NULL, end DATETIME NOT NULL, is_allday INTEGER NOT NULL, is_status INTEGER NOT NULL, sequence INTEGER NOT NULL)",
)


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _webasyst_root(tmp_path: Path) -> Path:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-config/apps.php",
        "<?php return ['team' => true, 'crm' => true];",
    )
    for app_id, name in (("team", "Team"), ("crm", "CRM")):
        _write(
            root,
            f"wa-apps/{app_id}/lib/config/app.php",
            "<?php return ["
            f"'name' => '{name}', "
            "'version' => '1.0.0', "
            "'vendor' => 'webasyst', "
            "'rights' => true"
            "];",
        )
    _write(
        root,
        "wa-system/webasyst/lib/config/app.php",
        "<?php return ["
        "'name' => 'Webasyst', "
        "'version' => '4.2.0', "
        "'vendor' => 'webasyst'"
        "];",
    )
    return root


async def _seed(database_url: str) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        for ddl in _EXTRA_DDL:
            await connection.exec_driver_sql(ddl)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    old = datetime(2020, 1, 1, 0, 0, 0)
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=42,
                    name="API User",
                    firstname="API",
                    login="api-user",
                    is_user=1,
                    create_datetime=old,
                    last_datetime=old,
                ),
                WaContactRow(
                    id=1,
                    name="Hidden",
                    firstname="Hidden",
                    login="hidden",
                    is_user=1,
                    create_datetime=old,
                ),
                WaContactRow(
                    id=2,
                    name="Bob",
                    firstname="Bob",
                    login="bob",
                    is_user=1,
                    create_datetime=old,
                ),
                WaContactRow(
                    id=3,
                    name="Alice",
                    firstname="Alice",
                    login="alice",
                    is_user=1,
                    create_datetime=old,
                ),
                WaContactRow(
                    id=4,
                    name="Group No Login",
                    firstname="Group",
                    login=None,
                    is_user=1,
                    create_datetime=old,
                ),
            )
        )
        session.add_all(
            (
                WaUserGroupRow(contact_id=1, group_id=4),
                WaUserGroupRow(contact_id=3, group_id=3),
                WaUserGroupRow(contact_id=4, group_id=3),
            )
        )
        session.add(
            WaContactEmailRow(
                contact_id=3,
                email="alice@example.test",
                sort=0,
            )
        )
        session.add_all(
            (
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="backend",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="manage_users_in_group.4",
                    value=-1,
                ),
                WaContactRightRow(
                    group_id=-2,
                    app_id="crm",
                    name="backend",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=3,
                    app_id="crm",
                    name="backend",
                    value=2,
                ),
            )
        )
        session.add(
            WaApiTokenRow(
                contact_id=42,
                client_id="team-client",
                token=TOKEN,
                scope="team",
                create_datetime=old,
                last_use_datetime=None,
                expires=None,
            )
        )
        await session.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_team_users_get_list_runs_through_production_api_runtime(
    tmp_path: Path,
) -> None:
    root = _webasyst_root(tmp_path)
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'team-users.db'}"
    await _seed(database_url)

    app = create_app_with_settings(
        Settings(
            database_url=database_url,
            webasyst_root=root,
            webasyst_public_root_url="https://public.example/",
            webasyst_server_timezone="UTC",
        )
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api.php/team.users.getList?access_token={TOKEN}"
            )
            full_crm = await client.get(
                f"/api.php/team.users.getList?access_token={TOKEN}"
                "&filter[access][crm]=full"
            )
            group = await client.get(
                "/api.php/team.users.getList",
                params=[
                    ("access_token", TOKEN),
                    ("filter[group_id][]", "3"),
                    ("filter[group_id][]", "3"),
                ],
            )
            hidden_group = await client.get(
                f"/api.php/team.users.getList?access_token={TOKEN}"
                "&filter[group_id]=4"
            )
            post_rejected = await client.post(
                f"/api.php/team.users.getList?access_token={TOKEN}"
            )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == [
        "API User",
        "Alice",
        "Bob",
    ]
    assert all(
        "Hidden" != item["name"]
        for item in response.json()
    )
    alice = next(
        item for item in response.json()
        if item["id"] == 3
    )
    assert alice == {
        "id": 3,
        "name": "Alice",
        "firstname": "Alice",
        "lastname": "",
        "middlename": "",
        "company": "",
        "login": "alice",
        "email": ["alice@example.test"],
        "phone": [],
        "locale": "",
        "jobtitle": "",
        "last_datetime": None,
        "_event": "",
        "birth_day": None,
        "birth_month": None,
        "create_datetime": "2020-01-01 00:00:00",
        "_online_status": "offline",
        "group_id": [3],
        "userpic": "https://public.example/wa-content/img/userpic.svg",
        "userpic_original_crop": (
            "https://public.example/wa-content/img/userpic.svg"
        ),
        "userpic_uploaded": False,
        "userpic_thumbs": {
            "16": "https://public.example/wa-content/img/userpic.svg",
            "32": "https://public.example/wa-content/img/userpic.svg",
            "96": "https://public.example/wa-content/img/userpic.svg",
            "144": "https://public.example/wa-content/img/userpic.svg",
        },
    }

    assert full_crm.status_code == 200
    assert [item["id"] for item in full_crm.json()] == [3]

    assert group.status_code == 200
    assert [item["id"] for item in group.json()] == [3, 4]
    assert group.json()[1]["login"] is None

    assert hidden_group.status_code == 200
    assert hidden_group.json() == []

    assert post_rejected.status_code == 405
    assert post_rejected.json()["error"] == "invalid_request"
