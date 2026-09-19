from dataclasses import FrozenInstanceError

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.services.pattern_matcher import (
    EventPatternMatched,
    EventPatternMatcher,
    EventPatternNotMatched,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
    PluginEventOwner,
)
from gomazon_webasyst.application.events.vo.patterns import (
    AnyEventSource,
    EventNamePrefix,
    ExactEventPattern,
    ExactEventSource,
    LegacyRegexEventPattern,
    PrefixEventPattern,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerNoResult,
    EventHandlerReturned,
    LegacyEventPayload,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey


class RecordingRegexMatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, EventName]] = []

    def match(self, expression: str, event_name: EventName):
        self.calls.append((expression, event_name))
        if expression == "/^backend_/":
            return EventPatternMatched()
        return EventPatternNotMatched()


def test_event_identity_and_owner_values_are_frozen() -> None:
    key = EventKey(AppId("shop"), EventName("backend_order"))
    owner = PluginEventOwner(PluginKey(AppId("shop"), PluginId("demo")))
    assert {key}
    assert {owner}
    with pytest.raises(FrozenInstanceError):
        key.name = EventName("other")  # type: ignore[misc]


@pytest.mark.parametrize("cls", [EventName, EventHandlerId, EventNamePrefix])
def test_open_event_values_reject_empty_strings(cls) -> None:
    with pytest.raises(ValueError):
        cls("")


def test_source_selectors_are_explicit_variants_not_magic_strings() -> None:
    exact = ExactEventSource(AppId("site"))
    any_source = AnyEventSource()
    assert exact.app_id == AppId("site")
    assert type(any_source).__name__ == "AnyEventSource"


def test_exact_and_prefix_patterns_match_without_regex_adapter_calls() -> None:
    regex = RecordingRegexMatcher()
    matcher = EventPatternMatcher(regex)

    assert isinstance(
        matcher.match(
            ExactEventPattern(EventName("backend_header")),
            EventName("backend_header"),
        ),
        EventPatternMatched,
    )
    assert isinstance(
        matcher.match(
            ExactEventPattern(EventName("backend_header")),
            EventName("frontend_header"),
        ),
        EventPatternNotMatched,
    )
    assert isinstance(
        matcher.match(
            PrefixEventPattern(EventNamePrefix("backend_")),
            EventName("backend_header"),
        ),
        EventPatternMatched,
    )
    assert regex.calls == []


def test_legacy_regex_pattern_delegates_to_compatibility_matcher() -> None:
    regex = RecordingRegexMatcher()
    matcher = EventPatternMatcher(regex)
    result = matcher.match(
        LegacyRegexEventPattern("/^backend_/"),
        EventName("backend_header"),
    )
    assert isinstance(result, EventPatternMatched)
    assert regex.calls == [("/^backend_/", EventName("backend_header"))]


def test_handler_outcome_uses_explicit_no_result_or_returned_payload() -> None:
    no_result = EventHandlerNoResult()
    returned = EventHandlerReturned(
        value=LegacyEventPayload(value={"ok": True})
    )
    assert type(no_result).__name__ == "EventHandlerNoResult"
    assert returned.value.value == {"ok": True}


def test_application_and_plugin_owners_are_distinct_types() -> None:
    app = ApplicationEventOwner(AppId("site"))
    plugin = PluginEventOwner(PluginKey(AppId("site"), PluginId("demo")))
    assert type(app) is not type(plugin)
