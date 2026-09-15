from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.persistent_values import (
    PersistentCredential,
    PersistentCredentialLifetime,
)
from gomazon_webasyst.contracts.auth import AuthIdentity
from gomazon_webasyst.contracts.enums import PersistentCredentialRejectReason
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    PersistentCredentialRejected,
    PersistentCredentialResolved,
    PersistentStrategyNotApplicable,
    PersistentStrategyRejected,
    PersistentStrategyResolved,
    RefreshPersistentCredential,
)
from gomazon_webasyst.infrastructure.auth.persistent_credentials import (
    OrderedPersistentCredentialResolver,
)


IDENTITY = AuthIdentity(
    id=42,
    login="admin",
    password_hash="hash",
    is_user=1,
    create_datetime=datetime(2026, 1, 1),
)
REFRESH = RefreshPersistentCredential(
    credential=PersistentCredential("legacy"),
    lifetime=PersistentCredentialLifetime(timedelta(days=30)),
)


class Strategy:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def resolve(self, credential):
        self.calls.append(credential)
        return self.result


@pytest.mark.asyncio
async def test_resolver_skips_not_applicable_and_returns_first_success():
    first = Strategy(PersistentStrategyNotApplicable())
    second = Strategy(PersistentStrategyResolved(identity=IDENTITY, disposition=REFRESH))
    third = Strategy(PersistentStrategyRejected(
        reason=PersistentCredentialRejectReason.INVALID,
        disposition=ClearPersistentCredential(),
    ))
    resolver = OrderedPersistentCredentialResolver((first, second, third))
    credential = PersistentCredential("opaque-v2-or-legacy")

    result = await resolver.resolve(credential)

    assert isinstance(result, PersistentCredentialResolved)
    assert result.identity.id == 42
    assert first.calls == [credential]
    assert second.calls == [credential]
    assert third.calls == []


@pytest.mark.asyncio
async def test_resolver_terminal_rejection_stops_later_strategies():
    first = Strategy(PersistentStrategyRejected(
        reason=PersistentCredentialRejectReason.MALFORMED,
        disposition=ClearPersistentCredential(),
    ))
    second = Strategy(PersistentStrategyResolved(identity=IDENTITY, disposition=REFRESH))
    resolver = OrderedPersistentCredentialResolver((first, second))

    result = await resolver.resolve(PersistentCredential("broken"))

    assert isinstance(result, PersistentCredentialRejected)
    assert result.reason is PersistentCredentialRejectReason.MALFORMED
    assert second.calls == []


@pytest.mark.asyncio
async def test_resolver_returns_explicit_unsupported_after_all_strategies_skip():
    resolver = OrderedPersistentCredentialResolver((
        Strategy(PersistentStrategyNotApplicable()),
        Strategy(PersistentStrategyNotApplicable()),
    ))

    result = await resolver.resolve(PersistentCredential("unknown-format"))

    assert isinstance(result, PersistentCredentialRejected)
    assert result.reason is PersistentCredentialRejectReason.UNSUPPORTED
    assert isinstance(result.disposition, ClearPersistentCredential)


@pytest.mark.asyncio
async def test_new_prefixed_strategy_can_be_registered_without_resolver_changes():
    opaque_identity = IDENTITY.model_copy(update={"id": 99, "login": "opaque"})
    opaque = Strategy(PersistentStrategyResolved(
        identity=opaque_identity,
        disposition=REFRESH,
    ))
    legacy = Strategy(PersistentStrategyRejected(
        reason=PersistentCredentialRejectReason.MALFORMED,
        disposition=ClearPersistentCredential(),
    ))
    resolver = OrderedPersistentCredentialResolver((opaque, legacy))

    result = await resolver.resolve(PersistentCredential("v2:abc"))

    assert isinstance(result, PersistentCredentialResolved)
    assert result.identity.id == 99
    assert legacy.calls == []
