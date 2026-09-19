from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

pytest.importorskip("aiosqlite")

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaApiTokenRow,
    WaContactCalendarRow,
    WaContactDataRow,
    WaContactEmailRow,
    WaContactEventRow,
    WaContactRightRow,
    WaContactRow,
    WaGroupRow,
    WaUserGroupRow,
)
from gomazon_webasyst.main import create_app_with_settings


TOKEN = "t" * 32


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
    _write(
        root,
        "wa-apps/team/lib/config/app.php",
        "<?php return ["
        "'name' => 'Team', "
        "'version' => '2.3.4', "
        "'vendor' => 'webasyst', "
        "'rights' => true, "
        "'plugins' => true, "
        "'csrf' => true"
        "];",
    )
    _write(
        root,
        "wa-apps/crm/lib/config/app.php",
        "<?php return ["
        "'name' => 'CRM', "
        "'version' => '1.0.0', "
        "'vendor' => 'example'"
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


async def _seed(container) -> datetime:
    now = datetime.now().replace(microsecond=0)
    sessions = async_sessionmaker(
        container.engine,
        expire_on_commit=False,
    )
    async with sessions() as session:
        session.add_all(
            (
                WaContactRow(
                    id=42,
                    name="Principal",
                    firstname="Principal",
                    is_user=1,
                    login="principal",
                    last_datetime=now,
                    create_datetime=now - timedelta(days=3),
                    locale="en_US",
                ),
                WaContactRow(
                    id=43,
                    name="Hidden User",
                    firstname="Hidden",
                    lastname="User",
                    is_user=1,
                    login="hidden",
                    last_datetime=now,
                    create_datetime=now - timedelta(days=2),
                    locale="en_US",
                ),
                WaContactRow(
                    id=44,
                    name="Visible User",
                    firstname="Visible",
                    lastname="User",
                    is_user=1,
                    login="visible",
                    last_datetime=now,
                    create_datetime=now - timedelta(days=1),
                    locale="en_US",
                    photo=12345,
                ),
                WaContactRow(
                    id=45,
                    name="Banned User",
                    firstname="Banned",
                    is_user=-1,
                    login="banned",
                    create_datetime=now,
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
                    description="hidden",
                ),
                WaGroupRow(
                    id=8,
                    name="Visible",
                    cnt=2,
                    sort=1,
                    type="location",
                    description="visible",
                ),
            )
        )
        session.add_all(
            (
                WaUserGroupRow(contact_id=42, group_id=8),
                WaUserGroupRow(contact_id=43, group_id=7),
                WaUserGroupRow(contact_id=44, group_id=8),
            )
        )
        session.add_all(
            (
                WaContactEmailRow(
                    contact_id=44,
                    email="visible@example.test",
                    sort=0,
                ),
                WaContactDataRow(
                    contact_id=44,
                    field="phone",
                    ext="mobile",
                    value="+123",
                    sort=0,
                    status="confirmed",
                ),
            )
        )
        session.add_all(
            (
                # Principal may call Team API.
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="backend",
                    value=1,
                ),
                # Hide group 7 but keep other groups visible.
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="manage_users_in_group.7",
                    value=-1,
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="team",
                    name="manage_users_in_group.all",
                    value=1,
                ),
                # Only visible user has full CRM access.
                WaContactRightRow(
                    group_id=-44,
                    app_id="crm",
                    name="backend",
                    value=2,
                ),
            )
        )
        session.add(
            WaApiTokenRow(
                contact_id=42,
                client_id="team-test",
                token=TOKEN,
                scope="team",
                create_datetime=now - timedelta(hours=1),
                last_use_datetime=None,
                expires=None,
            )
        )
        session.add(
            WaContactCalendarRow(
                id=5,
                name="Status",
                bg_color="#ffffff",
                font_color="#000000",
                status_bg_color="#111111",
                status_font_color="#eeeeee",
                icon="status",
                sort=0,
                is_limited=0,
                default_status=None,
            )
        )
        session.add(
            WaContactEventRow(
                id=10,
                uid="status-now",
                create_datetime=now - timedelta(days=1),
                update_datetime=now,
                contact_id=44,
                calendar_id=5,
                summary="Working",
                description=None,
                location=None,
                start=now - timedelta(minutes=5),
                end=now + timedelta(minutes=5),
                is_allday=0,
                is_status=1,
                sequence=0,
            )
        )
        await session.commit()
    return now


@pytest.mark.asyncio
async def test_team_directory_api_runs_through_production_runtime(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "team.db"
    root = _webasyst_root(tmp_path)
    app = create_app_with_settings(
        Settings(
            database_url=f"sqlite+aiosqlite:///{db_path}",
            webasyst_root=root,
            webasyst_timezone="UTC",
            webasyst_mod_rewrite=True,
        )
    )

    async with app.router.lifespan_context(app):
        async with app.state.container.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await _seed(app.state.container)

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://team.test",
        ) as client:
            users = await client.get(
                f"/api.php/team.users.getList?access_token={TOKEN}"
            )
            by_group = await client.get(
                f"/api.php/team.users.getList?access_token={TOKEN}"
                "&filter[group_id][]=8"
            )
            by_access = await client.get(
                f"/api.php/team.users.getList?access_token={TOKEN}"
                "&filter[access][crm]=full"
            )
            groups = await client.get(
                f"/api.php/team.groups.getList?access_token={TOKEN}"
            )
            locations = await client.get(
                f"/api.php/team.groups.getList?access_token={TOKEN}"
                "&filter[type][]=location"
            )

    assert users.status_code == 200
    users_payload = users.json()
    assert [item["id"] for item in users_payload] == [42, 44]
    assert all(item["id"] != 43 for item in users_payload)
    assert all(item["id"] != 45 for item in users_payload)

    visible = next(item for item in users_payload if item["id"] == 44)
    assert visible["email"] == ["visible@example.test"]
    assert visible["phone"] == [
        {
            "value": "+123",
            "ext": "mobile",
            "status": "confirmed",
        }
    ]
    assert visible["group_id"] == [8]
    assert visible["_online_status"] == "online"
    assert visible["_event"]["summary"] == "Working"
    assert visible["userpic"] == (
        "http://team.test/wa-data/public/contacts/photos/"
        "44/00/44/12345.144x144.jpg"
    )
    assert visible["userpic_thumbs"]["16"].endswith(
        "/12345.16x16.jpg"
    )

    assert by_group.status_code == 200
    assert [item["id"] for item in by_group.json()] == [42, 44]

    assert by_access.status_code == 200
    assert [item["id"] for item in by_access.json()] == [44]

    assert groups.status_code == 200
    assert [item["id"] for item in groups.json()] == [8]
    assert groups.json()[0]["type"] == "location"

    assert locations.status_code == 200
    assert [item["id"] for item in locations.json()] == [8]
