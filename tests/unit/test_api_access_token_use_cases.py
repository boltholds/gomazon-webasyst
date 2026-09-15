from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
)
from gomazon_webasyst.application.api_credentials import (
    IssueImplicitApiAccessToken,
    ResolveApiAccessToken,
    RevokeApiAccessToken,
)
from gomazon_webasyst.application.api_token_issuance import (
    ApiTokenIssueCollision,
    ApiTokenIssueConcurrentStateChanged,
    ApiTokenIssued,
)
from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenAlreadyMissing,
    ApiTokenRevoked,
    ApiTokenTouchMissing,
    ApiTokenTouched,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenAlreadyMissing,
    ApiAccessTokenIssueRejected,
    ApiAccessTokenIssued,
    ApiAccessTokenResolveRejected,
    ApiAccessTokenResolved,
    ApiAccessTokenRevoked,
    ApiTokenExpiresAt,
    ApiTokenLastUsedAt,
    ApiTokenMissing,
    ApiTokenNeverExpires,
    ApiTokenNeverUsed,
    ApiTokenResolved,
    StoredApiAccessToken,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    ApiAccessTokenIssueRejectReason,
    ApiAccessTokenResolveRejectReason,
)


NOW = datetime(2026, 9, 15, 12, 0, 0)
SUBJECT = AuthenticatedSubject(id=42, login="user")
CLIENT = ApiClientId("client")
SCOPE = ApiScope.of("shop")
TOKEN = ApiAccessToken("a" * 32)


class StubTokenIssuer:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    async def issue(self, contact_id, client_id, scope, uow):
        self.calls.append((contact_id, client_id, scope, uow))
        return self.result


class FakeTokens:
    def __init__(self, *, resolved=None, touch_result=None, revoke_result=None) -> None:
        self.resolved = resolved
        self.touch_result = touch_result
        self.revoke_result = revoke_result
        self.touches = []
        self.revokes = []

    async def resolve(self, token):
        return self.resolved

    async def touch_last_use(self, token, at):
        self.touches.append((token, at))
        return self.touch_result

    async def revoke(self, token):
        self.revokes.append(token)
        return self.revoke_result


class FakeUow:
    def __init__(self, tokens: FakeTokens) -> None:
        self.tokens = tokens
        self.authorization_codes = object()
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        raise AssertionError("explicit rollback is not expected")


def stored(*, expiry, last_use=None) -> StoredApiAccessToken:
    return StoredApiAccessToken(
        token=TOKEN,
        contact_id=42,
        client_id=CLIENT,
        scope=SCOPE,
        created_at=NOW - timedelta(days=1),
        last_use=last_use if last_use is not None else ApiTokenNeverUsed(),
        expiry=expiry,
    )


@pytest.mark.asyncio
async def test_implicit_issue_delegates_to_shared_issuer_and_commits() -> None:
    uow = FakeUow(FakeTokens())
    issuer = StubTokenIssuer(ApiTokenIssued(token=TOKEN, scope=SCOPE))
    use_case = IssueImplicitApiAccessToken(uow_factory=lambda: uow, token_issuer=issuer)

    result = await use_case(SUBJECT, CLIENT, SCOPE)

    assert isinstance(result, ApiAccessTokenIssued)
    assert result.access_token == TOKEN
    assert result.scope == SCOPE
    assert issuer.calls == [(42, CLIENT, SCOPE, uow)]
    assert uow.commits == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("issuer_result", "reason"),
    [
        (ApiTokenIssueCollision(token=TOKEN), ApiAccessTokenIssueRejectReason.TOKEN_COLLISION),
        (
            ApiTokenIssueConcurrentStateChanged(contact_id=42, client_id=CLIENT),
            ApiAccessTokenIssueRejectReason.CONCURRENT_STATE_CHANGED,
        ),
    ],
)
async def test_implicit_issue_maps_shared_issuer_negative_results_without_commit(
    issuer_result,
    reason,
) -> None:
    uow = FakeUow(FakeTokens())
    use_case = IssueImplicitApiAccessToken(
        uow_factory=lambda: uow,
        token_issuer=StubTokenIssuer(issuer_result),
    )

    result = await use_case(SUBJECT, CLIENT, SCOPE)

    assert isinstance(result, ApiAccessTokenIssueRejected)
    assert result.reason is reason
    assert uow.commits == 0


@pytest.mark.asyncio
async def test_resolve_unknown_token_is_explicit_missing_without_touch() -> None:
    tokens = FakeTokens(resolved=ApiTokenMissing(token=TOKEN))
    uow = FakeUow(tokens)
    use_case = ResolveApiAccessToken(uow_factory=lambda: uow, clock=lambda: NOW)

    result = await use_case(TOKEN)

    assert isinstance(result, ApiAccessTokenResolveRejected)
    assert result.reason is ApiAccessTokenResolveRejectReason.MISSING
    assert tokens.touches == []
    assert uow.commits == 0


@pytest.mark.asyncio
async def test_resolve_expired_token_is_rejected_without_touch() -> None:
    record = stored(expiry=ApiTokenExpiresAt(at=NOW - timedelta(seconds=1)))
    tokens = FakeTokens(resolved=ApiTokenResolved(record=record))
    uow = FakeUow(tokens)
    use_case = ResolveApiAccessToken(uow_factory=lambda: uow, clock=lambda: NOW)

    result = await use_case(TOKEN)

    assert isinstance(result, ApiAccessTokenResolveRejected)
    assert result.reason is ApiAccessTokenResolveRejectReason.EXPIRED
    assert tokens.touches == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expiry",
    [ApiTokenNeverExpires(), ApiTokenExpiresAt(at=NOW), ApiTokenExpiresAt(at=NOW + timedelta(seconds=1))],
)
async def test_resolve_valid_token_touches_last_use_and_returns_principal(expiry) -> None:
    record = stored(expiry=expiry)
    tokens = FakeTokens(
        resolved=ApiTokenResolved(record=record),
        touch_result=ApiTokenTouched(token=TOKEN, at=NOW),
    )
    uow = FakeUow(tokens)
    use_case = ResolveApiAccessToken(uow_factory=lambda: uow, clock=lambda: NOW)

    result = await use_case(TOKEN)

    assert isinstance(result, ApiAccessTokenResolved)
    assert result.access_token == TOKEN
    assert result.contact_id == 42
    assert result.client_id == CLIENT
    assert result.scope == SCOPE
    assert result.last_use == ApiTokenLastUsedAt(at=NOW)
    assert tokens.touches == [(TOKEN, NOW)]
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_resolve_touch_race_is_explicit_state_change_rejection() -> None:
    record = stored(expiry=ApiTokenNeverExpires())
    tokens = FakeTokens(
        resolved=ApiTokenResolved(record=record),
        touch_result=ApiTokenTouchMissing(token=TOKEN),
    )
    uow = FakeUow(tokens)
    use_case = ResolveApiAccessToken(uow_factory=lambda: uow, clock=lambda: NOW)

    result = await use_case(TOKEN)

    assert isinstance(result, ApiAccessTokenResolveRejected)
    assert result.reason is ApiAccessTokenResolveRejectReason.CONCURRENT_STATE_CHANGED
    assert uow.commits == 0


@pytest.mark.asyncio
async def test_revoke_token_commits_and_second_missing_result_is_idempotent() -> None:
    first_tokens = FakeTokens(revoke_result=ApiTokenRevoked(token=TOKEN))
    first_uow = FakeUow(first_tokens)
    first = RevokeApiAccessToken(uow_factory=lambda: first_uow)

    first_result = await first(TOKEN)

    assert isinstance(first_result, ApiAccessTokenRevoked)
    assert first_uow.commits == 1

    second_tokens = FakeTokens(revoke_result=ApiTokenAlreadyMissing(token=TOKEN))
    second_uow = FakeUow(second_tokens)
    second = RevokeApiAccessToken(uow_factory=lambda: second_uow)

    second_result = await second(TOKEN)

    assert isinstance(second_result, ApiAccessTokenAlreadyMissing)
    assert second_uow.commits == 0
