from datetime import datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaApiTokenRow,
    WaContactRightRow,
    WaContactRow,
    WaGroupRow,
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
        "<?php return ['team' => true];",
    )
    _write(
        root,
        "wa-apps/team/lib/config/app.php",
        "<?php return ["
        "'name' => 'Team', "
        "'icon' => 'img/team.svg', "
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
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    old = datetime(2020, 1, 1, 0, 0, 0)
    async with sessions() as session:
        session.add(
            WaContactRow(
                id=42,
                name="API User",
                firstname="API",
                is_user=1,
                login="api-user",
                create_datetime=old,
                last_datetime=old,
            )
        )
        session.add_all(
            [
                WaGroupRow(
                    id=2,
                    name="Office",
                    cnt=2,
                    icon=None,
                    sort=10,
                    type="location",
                    description=None,
                ),
                WaGroupRow(
                    id=4,
                    name="Hidden",
                    cnt=1,
                    icon=None,
                    sort=15,
                    type="group",
                    description="Secret",
                ),
                WaGroupRow(
                    id=1,
                    name="Engineering",
                    cnt=5,
                    icon=None,
                    sort=20,
                    type="group",
                    description="Developers",
                ),
                WaGroupRow(
                    id=3,
                    name="QA",
                    cnt=3,
                    icon=None,
                    sort=30,
                    type="group",
                    description=None,
                ),
            ]
        )
        session.add_all(
            [
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
            ]
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
async def test_team_groups_get_list_runs_through_production_runtime_and_legacy_db(
    tmp_path: Path,
) -> None:
    root = _webasyst_root(tmp_path)
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'team.db'}"
    await _seed(database_url)

    app = create_app_with_settings(
        Settings(
            database_url=database_url,
            webasyst_root=root,
        )
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api.php/team.groups.getList?access_token={TOKEN}"
            )
            filtered = await client.get(
                f"/api.php/team.groups.getList?access_token={TOKEN}"
                "&filter[type]=group"
            )
            repeated_types = await client.get(
                "/api.php/team.groups.getList",
                params=[
                    ("access_token", TOKEN),
                    ("filter[type][]", "group"),
                    ("filter[type][]", "location"),
                ],
            )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 2,
            "name": "Office",
            "cnt": 2,
            "type": "location",
            "description": None,
        },
        {
            "id": 1,
            "name": "Engineering",
            "cnt": 5,
            "type": "group",
            "description": "Developers",
        },
        {
            "id": 3,
            "name": "QA",
            "cnt": 3,
            "type": "group",
            "description": None,
        },
    ]

    assert filtered.status_code == 200
    assert filtered.json() == [
        {
            "id": 1,
            "name": "Engineering",
            "cnt": 5,
            "type": "group",
            "description": "Developers",
        },
        {
            "id": 3,
            "name": "QA",
            "cnt": 3,
            "type": "group",
            "description": None,
        },
    ]

    assert repeated_types.status_code == 200
    assert repeated_types.json() == response.json()
