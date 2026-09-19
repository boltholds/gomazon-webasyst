from pathlib import Path

import pytest

pytest.importorskip("aiosqlite")

from httpx import ASGITransport, AsyncClient

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.main import create_app_with_settings


@pytest.mark.asyncio
async def test_contact_http_vertical_slice_with_real_sqlalchemy_adapter(tmp_path: Path) -> None:
    db_path = tmp_path / "contacts.db"
    webasyst_root = tmp_path / "webasyst"
    (webasyst_root / "wa-config").mkdir(parents=True)
    (webasyst_root / "wa-system" / "webasyst" / "lib" / "config").mkdir(
        parents=True
    )
    (webasyst_root / "wa-config" / "apps.php").write_text(
        "<?php return [];",
        encoding="utf-8",
    )
    (
        webasyst_root
        / "wa-system"
        / "webasyst"
        / "lib"
        / "config"
        / "app.php"
    ).write_text(
        "<?php return ['name' => 'Webasyst', 'version' => '4.2.0', "
        "'vendor' => 'webasyst'];",
        encoding="utf-8",
    )
    app = create_app_with_settings(
        Settings(
            database_url=f"sqlite+aiosqlite:///{db_path}",
            webasyst_root=webasyst_root,
        )
    )

    async with app.router.lifespan_context(app):
        async with app.state.container.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/contacts",
                json={"name": "Alice", "firstname": "Alice"},
            )
            assert created.status_code == 201
            contact_id = created.json()["id"]

            loaded = await client.get(f"/api/v1/contacts/{contact_id}")
            assert loaded.status_code == 200
            assert loaded.json()["name"] == "Alice"

            updated = await client.patch(
                f"/api/v1/contacts/{contact_id}",
                json={"company": "Example Ltd"},
            )
            assert updated.status_code == 200
            assert updated.json()["company"] == "Example Ltd"
