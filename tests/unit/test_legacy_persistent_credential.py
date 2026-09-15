from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.compatibility.webasyst.auth.persistent import (
    LEGACY_AUTH_TOKEN_LIFETIME,
    LegacyAuthTokenIssuer,
    LegacyAuthTokenParser,
    LegacyAuthTokenStrategy,
    LegacyTokenMalformed,
    LegacyTokenParsed,
)
from gomazon_webasyst.compatibility.webasyst.auth.tokens import LegacyCredentialVersionTokenFactory
from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    SubjectResolved,
    SubjectResolutionError,
)
from gomazon_webasyst.contracts.enums import (
    PersistentCredentialRejectReason,
    SubjectResolutionErrorType,
)
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    PersistentCredentialIssued,
    PersistentStrategyRejected,
    PersistentStrategyResolved,
    RefreshPersistentCredential,
)


IDENTITY = AuthIdentity(
    id=42,
    login="admin",
    password_hash="5ebe2294ecd0e0f08eab7690d2a6ee69",
    is_user=1,
    create_datetime=datetime(2026, 1, 1, 12, 34, 56),
)


class SubjectStore:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def get(self, subject_id):
        self.calls.append(subject_id)
        return self.result


def test_legacy_parser_extracts_contact_id_between_15_char_hash_parts():
    token = LegacyCredentialVersionTokenFactory().create(IDENTITY)

    parsed = LegacyAuthTokenParser().parse(PersistentCredential(token))

    assert isinstance(parsed, LegacyTokenParsed)
    assert parsed.credential.contact_id == 42
    assert parsed.credential.credential == PersistentCredential(token)


def test_legacy_parser_rejects_malformed_without_subject_lookup_shape():
    parsed = LegacyAuthTokenParser().parse(PersistentCredential("not-a-token"))

    assert isinstance(parsed, LegacyTokenMalformed)


@pytest.mark.asyncio
async def test_legacy_strategy_success_refreshes_same_value_for_30_days():
    token = LegacyCredentialVersionTokenFactory().create(IDENTITY)
    store = SubjectStore(SubjectResolved(identity=IDENTITY))
    strategy = LegacyAuthTokenStrategy(
        subject_store=store,
        token_factory=LegacyCredentialVersionTokenFactory(),
    )

    result = await strategy.resolve(PersistentCredential(token))

    assert isinstance(result, PersistentStrategyResolved)
    assert result.identity == IDENTITY
    assert isinstance(result.disposition, RefreshPersistentCredential)
    assert result.disposition.credential == PersistentCredential(token)
    assert result.disposition.lifetime == LEGACY_AUTH_TOKEN_LIFETIME
    assert LEGACY_AUTH_TOKEN_LIFETIME.value == timedelta(days=30)


@pytest.mark.asyncio
async def test_legacy_strategy_invalid_or_stale_token_clears_credential():
    store = SubjectStore(SubjectResolved(identity=IDENTITY))
    expected = LegacyCredentialVersionTokenFactory().create(IDENTITY)
    stale = expected[:-1] + ("0" if expected[-1] != "0" else "1")
    strategy = LegacyAuthTokenStrategy(
        subject_store=store,
        token_factory=LegacyCredentialVersionTokenFactory(),
    )

    result = await strategy.resolve(PersistentCredential(stale))

    assert isinstance(result, PersistentStrategyRejected)
    assert result.reason is PersistentCredentialRejectReason.INVALID
    assert isinstance(result.disposition, ClearPersistentCredential)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("subject_result", "reason"),
    [
        (
            SubjectResolutionError(type=SubjectResolutionErrorType.NOT_FOUND),
            PersistentCredentialRejectReason.SUBJECT_NOT_FOUND,
        ),
        (
            SubjectResolutionError(type=SubjectResolutionErrorType.DISABLED),
            PersistentCredentialRejectReason.SUBJECT_DISABLED,
        ),
    ],
)
async def test_legacy_strategy_maps_subject_resolution_errors(subject_result, reason):
    token = LegacyCredentialVersionTokenFactory().create(IDENTITY)
    strategy = LegacyAuthTokenStrategy(
        subject_store=SubjectStore(subject_result),
        token_factory=LegacyCredentialVersionTokenFactory(),
    )

    result = await strategy.resolve(PersistentCredential(token))

    assert isinstance(result, PersistentStrategyRejected)
    assert result.reason is reason
    assert isinstance(result.disposition, ClearPersistentCredential)


@pytest.mark.asyncio
async def test_legacy_issuer_uses_existing_credential_token_factory_and_30_day_lifetime():
    issuer = LegacyAuthTokenIssuer(LegacyCredentialVersionTokenFactory())

    result = await issuer.issue(IDENTITY)

    assert isinstance(result, PersistentCredentialIssued)
    assert result.credential == PersistentCredential(
        LegacyCredentialVersionTokenFactory().create(IDENTITY)
    )
    assert result.lifetime == LEGACY_AUTH_TOKEN_LIFETIME
