from gomazon_webasyst.application.events.services.pattern_matcher import (
    EventPatternMatch,
    LegacyRegexEventMatcher,
)
from gomazon_webasyst.application.events.vo.identity import EventName


class LegacyEventRegexUnsupported(ValueError):
    pass


class RejectUnsupportedLegacyRegexMatcher(LegacyRegexEventMatcher):
    def match(
        self,
        expression: str,
        event_name: EventName,
    ) -> EventPatternMatch:
        raise LegacyEventRegexUnsupported(
            "raw Webasyst PCRE event patterns are not enabled in this runtime slice: "
            f"{expression!r} for {event_name.value!r}"
        )
