import json
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
)
from gomazon_webasyst.main import create_app_with_settings


TOKEN = "i" * 32
DENIED_TOKEN = "d" * 32
OLD = datetime(2020, 1, 1, 0, 0, 0)


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
        "<?php return ['team' => true];",
    )
    _write(
        root,
        "wa-apps/team/lib/config/app.php",
        "<?php return ["
        "'name' => 'Team', "
        "'version' => '2.3.4', "
        "'vendor' => 'webasyst', "
        "'system' => true, "
        "'rights' => true, "
        "'plugins' => true"
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
        await connection.exec_driver_sql(
            "CREATE TABLE wa_app_tokens ("
            "contact_id INTEGER, app_id TEXT NOT NULL, type TEXT NOT NULL, "
            "create_datetime DATETIME NOT NULL, expire_datetime DATETIME, "
            "token TEXT PRIMARY KEY NOT NULL, data TEXT)"
        )

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=42,
                    name="API Actor",
                    firstname="API",
                    login="actor",
                    is_user=1,
                    locale="en_US",
                    create_datetime=OLD,
                    last_datetime=OLD,
                ),
                WaContactRow(
                    id=43,
                    name="Denied Actor",
                    firstname="Denied",
                    login="denied",
                    is_user=1,
                    locale="en_US",
                    create_datetime=OLD,
                    last_datetime=OLD,
                ),
                WaContactRow(
                    id=90,
                    name="Existing User",
                    login="existing",
                    is_user=1,
                    create_datetime=OLD,
                ),
                WaContactEmailRow(
                    contact_id=90,
                    email="existing@example.test",
                    sort=0,
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="backend",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="add_users",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="manage_group.2",
                    value=1,
                ),
                WaApiTokenRow(
                    contact_id=42,
                    client_id="team-client",
                    token=TOKEN,
                    scope="team",
                    create_datetime=OLD,
                    last_use_datetime=None,
                    expires=None,
                ),
                WaContactRightRow(
                    group_id=-43,
                    app_id="team",
                    name="backend",
                    value=1,
                ),
                WaApiTokenRow(
                    contact_id=43,
                    client_id="denied-client",
                    token=DENIED_TOKEN,
                    scope="team",
                    create_datetime=OLD,
                    last_use_datetime=None,
                    expires=None,
                ),
            )
        )
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_team_users_invite_runs_through_production_api_runtime(
    tmp_path: Path,
) -> None:
    root = _webasyst_root(tmp_path)
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'team-invite.db'}"
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
            link = await client.post(
                f"/api.php/team.users.invite?access_token={TOKEN}",
                content=(
                    "email=new%40example.test&send=0"
                    "&groups%5B%5D=2&groups%5B%5D=3"
                ),
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            associative_groups = await client.post(
                f"/api.php/team.users.invite?access_token={TOKEN}",
                content=(
                    "email=assoc%40example.test"
                    "&groups%5Balpha%5D=2"
                    "&groups%5Bnested%5D%5Bchild%5D=7"
                    "&groups%5B%5D=3"
                ),
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            nested_only_groups = await client.post(
                f"/api.php/team.users.invite?access_token={TOKEN}",
                content=(
                    "email=nested-only%40example.test"
                    "&groups%5Bmeta%5D%5Bname%5D=engineering"
                ),
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            repeated = await client.post(
                f"/api.php/team.users.invite?access_token={TOKEN}",
                content="email=new%40example.test&send=false",
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            code = await client.post(
                f"/api.php/team.users.invite?access_token={TOKEN}",
                content="type=code",
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            send_unavailable = await client.post(
                f"/api.php/team.users.invite?access_token={TOKEN}",
                content="email=mail%40example.test&send=true",
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            denied = await client.post(
                f"/api.php/team.users.invite?access_token={DENIED_TOKEN}",
                content="email=denied-target%40example.test",
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            conflict = await client.post(
                f"/api.php/team.users.invite?access_token={TOKEN}",
                content="email=existing%40example.test",
                headers={
                    "content-type": "application/x-www-form-urlencoded"
                },
            )
            get_rejected = await client.get(
                f"/api.php/team.users.invite?access_token={TOKEN}"
            )

    assert link.status_code == 200
    body = link.json()
    assert set(body) == {
        "contact_id",
        "invitation_link",
        "invitation_expire",
    }
    assert body["invitation_link"].startswith(
        "https://public.example/link.php/"
    )

    assert repeated.status_code == 200
    assert repeated.json()["contact_id"] == body["contact_id"]

    assert associative_groups.status_code == 200
    associative_contact_id = associative_groups.json()["contact_id"]
    assert associative_contact_id != body["contact_id"]

    assert nested_only_groups.status_code == 200
    nested_only_contact_id = nested_only_groups.json()["contact_id"]
    assert nested_only_contact_id not in {
        body["contact_id"],
        associative_contact_id,
    }

    assert code.status_code == 200
    assert set(code.json()) == {"contact_id"}
    assert code.json()["contact_id"] != body["contact_id"]

    assert send_unavailable.status_code == 400
    assert send_unavailable.json()["error"] == "email_send_fail"
    assert send_unavailable.json()["contact_id"] > 0

    assert denied.status_code == 403
    assert denied.json() == {"error": "Access denied"}

    assert conflict.status_code == 409
    assert conflict.json() == {
        "error": "user_in_team",
        "contact_id": 90,
        "error_description": "Already in our team!",
    }

    assert get_rejected.status_code == 405
    assert get_rejected.json()["error"] == "invalid_request"

    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT contact_id, type, data "
                    "FROM wa_app_tokens ORDER BY create_datetime, token"
                )
            )
        ).mappings().all()
        link_rows = [
            row
            for row in rows
            if row["contact_id"] == body["contact_id"]
            and row["type"] == "user_invite"
        ]
        assert len(link_rows) == 2
        first_data = json.loads(link_rows[0]["data"])
        second_data = json.loads(link_rows[1]["data"])
        assert {tuple(item.get("groups", [])) for item in (first_data, second_data)} == {
            (),
            (2,),
        }

        associative_row = next(
            row
            for row in rows
            if row["contact_id"] == associative_contact_id
            and row["type"] == "user_invite"
        )
        assert json.loads(associative_row["data"]) == {
            "full_access": False,
            "groups": [2],
        }

        nested_only_row = next(
            row
            for row in rows
            if row["contact_id"] == nested_only_contact_id
            and row["type"] == "user_invite"
        )
        assert json.loads(nested_only_row["data"]) == {
            "full_access": False,
            "groups": [],
        }

        mail_contact_id = send_unavailable.json()["contact_id"]
        mail_rows = [
            row
            for row in rows
            if row["contact_id"] == mail_contact_id
            and row["type"] == "user_invite"
        ]
        assert len(mail_rows) == 1

        code_rows = [
            row
            for row in rows
            if row["contact_id"] == code.json()["contact_id"]
        ]
        assert len(code_rows) == 1
        assert code_rows[0]["type"] == "waid_invite"

        contacts = (
            await session.execute(
                text(
                    "SELECT id, create_app_id, create_method, create_contact_id "
                    "FROM wa_contact "
                    "WHERE id IN (:link_id, :code_id, :mail_id)"
                ),
                {
                    "link_id": body["contact_id"],
                    "code_id": code.json()["contact_id"],
                    "mail_id": mail_contact_id,
                },
            )
        ).mappings().all()
        assert all(row["create_app_id"] == "team" for row in contacts)
        assert all(row["create_method"] == "invite" for row in contacts)
        assert all(row["create_contact_id"] == 42 for row in contacts)

    await engine.dispose()
