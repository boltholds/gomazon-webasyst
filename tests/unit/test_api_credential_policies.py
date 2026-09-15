from datetime import datetime, timedelta, timezone

from gomazon_webasyst.application.api_credential_values import ApiScope
from gomazon_webasyst.application.ports.api_credential_policies import (
    ConsumeAuthorizationCode,
    CreateApiToken,
    KeepAuthorizationCode,
    ReuseApiToken,
    ReuseApiTokenWithScopeUpdate,
)
from gomazon_webasyst.compatibility.webasyst.api_credentials import (
    LegacyApiScopeCodec,
    WebasystApiCredentialGenerator,
    WebasystApiTokenIssuePolicy,
    WebasystAuthorizationCodeExchangePolicy,
    WebasystAuthorizationCodeLifetime,
)
from gomazon_webasyst.contracts.api_credentials import ApiTokenNeverExpires


def test_webasyst_generator_emits_lowercase_32_hex_chars() -> None:
    generator = WebasystApiCredentialGenerator()

    for value in (
        generator.authorization_code().value,
        generator.access_token().value,
    ):
        assert len(value) == 32
        assert value == value.lower()
        int(value, 16)


def test_legacy_code_lifetime_is_exactly_180_seconds() -> None:
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    assert WebasystAuthorizationCodeLifetime().expires_at(now) == now + timedelta(seconds=180)


def test_webasyst_exchange_policy_keeps_code_and_strict_variant_remains_representable() -> None:
    disposition = WebasystAuthorizationCodeExchangePolicy().disposition()

    assert isinstance(disposition, KeepAuthorizationCode)
    assert isinstance(ConsumeAuthorizationCode(), ConsumeAuthorizationCode)


def test_legacy_scope_codec_round_trips_ordered_unique_scope() -> None:
    codec = LegacyApiScopeCodec()
    scope = ApiScope.of("shop", "site", "shop")

    encoded = codec.encode(scope)
    decoded = codec.decode(encoded)

    assert encoded == "shop,site"
    assert decoded == ApiScope.of("shop", "site")


def test_webasyst_issue_policy_reuses_same_scope_without_write() -> None:
    policy = WebasystApiTokenIssuePolicy()

    result = policy.for_existing(ApiScope.of("shop"), ApiScope.of("shop"))

    assert isinstance(result, ReuseApiToken)


def test_webasyst_issue_policy_reuses_token_and_updates_changed_scope() -> None:
    policy = WebasystApiTokenIssuePolicy()
    requested = ApiScope.of("site", "shop")

    result = policy.for_existing(ApiScope.of("shop"), requested)

    assert isinstance(result, ReuseApiTokenWithScopeUpdate)
    assert result.scope == requested


def test_webasyst_issue_policy_creates_new_never_expiring_token_when_missing() -> None:
    result = WebasystApiTokenIssuePolicy().for_missing()

    assert isinstance(result, CreateApiToken)
    assert isinstance(result.expiry, ApiTokenNeverExpires)
