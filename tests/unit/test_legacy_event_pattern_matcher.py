import pytest

from gomazon_webasyst.application.events.vo.identity import EventName
from gomazon_webasyst.compatibility.webasyst.events.pattern_matcher import (
    LegacyEventRegexUnsupported,
    RejectUnsupportedLegacyRegexMatcher,
)


def test_raw_pcre_is_explicitly_fail_closed_until_compatibility_is_implemented() -> None:
    with pytest.raises(LegacyEventRegexUnsupported, match="PCRE"):
        RejectUnsupportedLegacyRegexMatcher().match(
            "/^backend_/",
            EventName("backend_header"),
        )
