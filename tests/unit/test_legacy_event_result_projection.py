from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
    EventDispatchResult,
)
from gomazon_webasyst.application.events.vo.identity import EventHandlerId, EventKey, EventName
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
    PluginEventOwner,
)
from gomazon_webasyst.application.events.vo.payload import LegacyEventPayload
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.compatibility.webasyst.events.result_projection import (
    LegacyEventArrayKeys,
    LegacyEventArrayKeysDisabled,
    LegacyEventResultProjector,
)


def _report(*results: EventDispatchResult, event_app: str = "site") -> EventDispatchReport:
    return EventDispatchReport(
        event=EventKey(AppId(event_app), EventName("backend_header")),
        results=results,
        failures=(),
    )


def test_application_result_key_is_app_id_and_is_not_array_keys_padded() -> None:
    report = _report(
        EventDispatchResult(
            handler_id=EventHandlerId("app"),
            owner=ApplicationEventOwner(AppId("blog")),
            value=LegacyEventPayload(value="scalar"),
        )
    )
    projected = LegacyEventResultProjector().project(
        report,
        array_keys=LegacyEventArrayKeys(("html",)),
    )
    assert projected == {"blog": "scalar"}


def test_same_app_plugin_result_key_matches_legacy_plugin_suffix() -> None:
    report = _report(
        EventDispatchResult(
            handler_id=EventHandlerId("plugin"),
            owner=PluginEventOwner(
                PluginKey(AppId("site"), PluginId("demo"))
            ),
            value=LegacyEventPayload(value={"html": "<b>x</b>"}),
        )
    )
    projected = LegacyEventResultProjector().project(
        report,
        array_keys=LegacyEventArrayKeysDisabled(),
    )
    assert projected == {"demo-plugin": {"html": "<b>x</b>"}}


def test_cross_app_plugin_result_key_contains_owner_app_id() -> None:
    report = _report(
        EventDispatchResult(
            handler_id=EventHandlerId("plugin"),
            owner=PluginEventOwner(
                PluginKey(AppId("site"), PluginId("rublesign"))
            ),
            value=LegacyEventPayload(value="x"),
        ),
        event_app="shop",
    )
    projected = LegacyEventResultProjector().project(
        report,
        array_keys=LegacyEventArrayKeysDisabled(),
    )
    assert projected == {"site_rublesign-plugin": "x"}


def test_plugin_scalar_is_wrapped_and_missing_or_null_keys_are_padded() -> None:
    scalar_report = _report(
        EventDispatchResult(
            handler_id=EventHandlerId("scalar"),
            owner=PluginEventOwner(
                PluginKey(AppId("site"), PluginId("demo"))
            ),
            value=LegacyEventPayload(value="scalar"),
        )
    )
    assert LegacyEventResultProjector().project(
        scalar_report,
        array_keys=LegacyEventArrayKeys(("html", "sidebar")),
    ) == {
        "demo-plugin": {
            "": "scalar",
            "html": "",
            "sidebar": "",
        }
    }

    mapping_report = _report(
        EventDispatchResult(
            handler_id=EventHandlerId("mapping"),
            owner=PluginEventOwner(
                PluginKey(AppId("site"), PluginId("demo"))
            ),
            value=LegacyEventPayload(value={"html": None, "keep": 1}),
        )
    )
    assert LegacyEventResultProjector().project(
        mapping_report,
        array_keys=LegacyEventArrayKeys(("html", "sidebar")),
    ) == {
        "demo-plugin": {
            "html": "",
            "keep": 1,
            "sidebar": "",
        }
    }
