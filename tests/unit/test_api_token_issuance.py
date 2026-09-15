from datetime import datetime

import pytest

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
)
from gomazon_webasyst.application.api_token_issuance import (
    ApiTokenIssueCollision,
    ApiTokenIssued,
    ApiTokenIssuer,
)
from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenForSubjectClientFound,
    ApiTokenForSubjectClientMissing,
    ApiTokenScopeUpdated,
    ApiTokenStored,
    ApiTokenSubjectClientCollision,
    ApiTokenValueCollision,
)
from gomazon_webasyst.compatibility.webasyst.api_credentials import WebasystApiTokenIssuePolicy
from gomazon_webasyst.contracts.api_credentials import (
    ApiTokenNeverExpires,
    ApiTokenNeverUsed,
    StoredApiAccessToken,
)


NOW = datetime(2026, 9, 15, 12, 0, 0)
CLIENT = ApiClientId("client")


class FixedGenerator:
    def __init__(self, token: str) -> None:
        self._token = ApiAccessToken(token)

    def authorization_code(self):
        raise AssertionError("authorization code generation is not used here")

    def access_token(self) -> ApiAccessToken:
        return self._token


class FakeTokenRepository:
    def __init__(self, lookups, *, create_result=None) -> None:
        self.lookups = list(lookups)
        self.create_result = create_result
        self.created = []
        self.updated_scope = []

    async def find_for_subject_client(self, contact_id, client_id):
        assert contact_id == 42
        assert client_id == CLIENT
        return self.lookups.pop(0)

    async def create(self, record):
        self.created.append(record)
        result = self.create_result
        if callable(result):
            return result(record)
        return result

    async def update_scope(self, token, scope):
        self.updated_scope.append((token, scope))
        return ApiTokenScopeUpdated(token=token, scope=scope)


class FakeUow:
    def __init__(self, tokens: FakeTokenRepository) -> None:
        self.tokens = tokens


def stored(token: str = "a" * 32, scope: ApiScope = ApiScope.of("shop")) -> StoredApiAccessToken:
    return StoredApiAccessToken(
        token=ApiAccessToken(token),
        contact_id=42,
        client_id=CLIENT,
        scope=scope,
        created_at=NOW,
        last_use=ApiTokenNeverUsed(),
        expiry=ApiTokenNeverExpires(),
    )


def issuer(token: str = "b" * 32) -> ApiTokenIssuer:
    return ApiTokenIssuer(
        generator=FixedGenerator(token),
        issue_policy=WebasystApiTokenIssuePolicy(),
        clock=lambda: NOW,
    )


@pytest.mark.asyncio
async def test_existing_subject_client_token_is_reused_without_write_when_scope_matches() -> None:
    existing = stored()
    repo = FakeTokenRepository([ApiTokenForSubjectClientFound(record=existing)])

    result = await issuer().issue(42, CLIENT, ApiScope.of("shop"), FakeUow(repo))

    assert isinstance(result, ApiTokenIssued)
    assert result.token == existing.token
    assert result.scope == existing.scope
    assert repo.created == []
    assert repo.updated_scope == []


@pytest.mark.asyncio
async def test_existing_subject_client_token_is_reused_and_scope_updated() -> None:
    existing = stored()
    requested = ApiScope.of("site")
    repo = FakeTokenRepository([ApiTokenForSubjectClientFound(record=existing)])

    result = await issuer().issue(42, CLIENT, requested, FakeUow(repo))

    assert isinstance(result, ApiTokenIssued)
    assert result.token == existing.token
    assert result.scope == requested
    assert repo.updated_scope == [(existing.token, requested)]
    assert repo.created == []


@pytest.mark.asyncio
async def test_missing_subject_client_token_is_generated_and_stored_never_expiring() -> None:
    requested = ApiScope.of("shop", "site")
    repo = FakeTokenRepository(
        [ApiTokenForSubjectClientMissing(contact_id=42, client_id=CLIENT)],
        create_result=lambda record: ApiTokenStored(record=record),
    )

    result = await issuer("c" * 32).issue(42, CLIENT, requested, FakeUow(repo))

    assert isinstance(result, ApiTokenIssued)
    assert result.token == ApiAccessToken("c" * 32)
    assert result.scope == requested
    assert len(repo.created) == 1
    created = repo.created[0]
    assert created.created_at == NOW
    assert isinstance(created.last_use, ApiTokenNeverUsed)
    assert isinstance(created.expiry, ApiTokenNeverExpires)


@pytest.mark.asyncio
async def test_subject_client_create_race_reloads_winner_and_applies_requested_scope() -> None:
    requested = ApiScope.of("site")
    winner = stored(token="d" * 32, scope=ApiScope.of("shop"))
    repo = FakeTokenRepository(
        [
            ApiTokenForSubjectClientMissing(contact_id=42, client_id=CLIENT),
            ApiTokenForSubjectClientFound(record=winner),
        ],
        create_result=ApiTokenSubjectClientCollision(contact_id=42, client_id=CLIENT),
    )

    result = await issuer("c" * 32).issue(42, CLIENT, requested, FakeUow(repo))

    assert isinstance(result, ApiTokenIssued)
    assert result.token == winner.token
    assert result.scope == requested
    assert repo.updated_scope == [(winner.token, requested)]


@pytest.mark.asyncio
async def test_random_token_value_collision_is_explicit_issue_result() -> None:
    collision = ApiAccessToken("c" * 32)
    repo = FakeTokenRepository(
        [ApiTokenForSubjectClientMissing(contact_id=42, client_id=CLIENT)],
        create_result=ApiTokenValueCollision(token=collision),
    )

    result = await issuer(collision.value).issue(42, CLIENT, ApiScope.of("shop"), FakeUow(repo))

    assert isinstance(result, ApiTokenIssueCollision)
    assert result.token == collision
