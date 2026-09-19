from pathlib import Path

import pytest

pytest.importorskip("aiosqlite")

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
)
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerReturned,
    LegacyEventPayload,
)
from gomazon_webasyst.application.ports.event_handlers import (
    EventHandlerContext,
    EventHandlerRegistered,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.main import create_app_with_settings


class TeamCollectionSubscriber:
    async def handle(self, context: EventHandlerContext, payload):
        return EventHandlerReturned(
            value=LegacyEventPayload(
                value={"handled": True}
            )
        )


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _root(tmp_path: Path) -> Path:
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
        "'vendor' => 'webasyst'"
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


@pytest.mark.asyncio
async def test_team_contacts_collection_bridge_uses_shared_event_runtime(
    tmp_path: Path,
) -> None:
    app = create_app_with_settings(
        Settings(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'events.db'}",
            webasyst_root=_root(tmp_path),
        )
    )

    async with app.router.lifespan_context(app):
        runtime = app.state.container.application_runtime
        request = EventDispatchRequest(
            event=EventKey(
                AppId("contacts"),
                EventName("contacts_collection"),
            ),
            payload=LegacyEventPayload(
                value={"hash": "users"}
            ),
        )

        without_nested = await runtime.event_dispatcher.dispatch(
            request
        )
        assert len(without_nested.results) == 1
        assert without_nested.results[0].owner == (
            ApplicationEventOwner(AppId("team"))
        )
        assert without_nested.results[0].value.value is False

        registered = runtime.event_registry.register(
            EventHandlerDefinition(
                handler_id=EventHandlerId(
                    "test.team.contacts_collection"
                ),
                owner=ApplicationEventOwner(AppId("test")),
                source=ExactEventSource(AppId("team")),
                pattern=ExactEventPattern(
                    EventName("contacts_collection")
                ),
                handler=TeamCollectionSubscriber(),
            )
        )
        assert isinstance(registered, EventHandlerRegistered)

        with_nested = await runtime.event_dispatcher.dispatch(request)
        assert len(with_nested.results) == 1
        assert with_nested.results[0].value.value is True
        assert with_nested.failures == ()
