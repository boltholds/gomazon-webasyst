from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.api_credentials import (
    ExchangeAuthorizationCode,
    IssueAuthorizationCode,
)
from gomazon_webasyst.application.api_token_issuance import ApiTokenIssued
from gomazon_webasyst.application.ports.api_credential_policies import (
    ConsumeAuthorizationCode,
    KeepAuthorizationCode,
)
from gomazon_webasyst.application.ports.api_credentials import (
    AuthorizationCodeCreateCollision,
    AuthorizationCodeDeleted,
    AuthorizationCodeFound,
    AuthorizationCodeMissing,
    AuthorizationCodeStored,
)
from gomazon_webasyst.contracts.api_credentials import (
    AuthorizationCodeExchangeRejected,
    AuthorizationCodeExchanged,
    AuthorizationCodeIssueRejected,
    AuthorizationCodeIssued,
    StoredAuthorizationCode,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    AuthorizationCodeExchangeRejectReason,
    AuthorizationCodeIssueRejectReason,
)


NOW = datetime(2026, 9, 15, 12, 0, 0)
SUBJECT = AuthenticatedSubject(id=42, login="user")
CLIENT = ApiClientId("client")
SCOPE = ApiScope.of("shop", "site")
CODE = AuthorizationCode("a" * 32)
TOKEN = ApiAccessToken("b" * 32)


class FixedGenerator:
    def authorization_code(self) -> AuthorizationCode:
        return CODE

    def access_token(self):
        raise AssertionError("token generation belongs to shared issuer")


class Lifetime180:
    def expires_at(self, now: datetime) -> datetime:
        return now + timedelta(seconds=180)


class FixedExchangePolicy:
    def __init__(self, disposition) -> None:
        self._disposition = disposition

    def disposition(self):
        return self._disposition


class FakeCodes:
    def __init__(self, *, create_result=None, resolve_result=None, delete_result=None) -> None:
        self.create_result = create_result
        self.resolve_result = resolve_result
        self.delete_result = delete_result
        self.created = []
        self.deleted = []

    async def create(self, record):
        self.created.append(record)
        if callable(self.create_result):
            return self.create_result(record)
        return self.create_result

    async def resolve(self, code):
        return self.resolve_result

    async def delete(self, code):
        self.deleted.append(code)
        return self.delete_result


class FakeUow:
    def __init__(self, codes: FakeCodes) -> None:
        self.authorization_codes = codes
        self.tokens = object()
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        raise AssertionError("explicit rollback is not expected")


class StubTokenIssuer:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    async def issue(self, contact_id, client_id, scope, uow):
        self.calls.append((contact_id, client_id, scope, uow))
        return self.result


def code_record(*, client_id: ApiClientId = CLIENT, expires_at: datetime | None = None):
    return StoredAuthorizationCode(
        code=CODE,
        contact_id=42,
        client_id=client_id,
        scope=SCOPE,
        expires_at=expires_at if expires_at is not None else NOW + timedelta(seconds=180),
    )


@pytest.mark.asyncio
async def test_issue_authorization_code_uses_policy_lifetime_persists_and_commits() -> None:
    codes = FakeCodes(create_result=lambda record: AuthorizationCodeStored(record=record))
    uow = FakeUow(codes)
    use_case = IssueAuthorizationCode(
        uow_factory=lambda: uow,
        generator=FixedGenerator(),
        lifetime_policy=Lifetime180(),
        clock=lambda: NOW,
    )

    result = await use_case(SUBJECT, CLIENT, SCOPE)

    assert isinstance(result, AuthorizationCodeIssued)
    assert result.record.code == CODE
    assert result.record.contact_id == 42
    assert result.record.expires_at == NOW + timedelta(seconds=180)
    assert codes.created == [result.record]
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_issue_authorization_code_retries_collision_and_commits_first_success() -> None:
    first = AuthorizationCode("c" * 32)
    second = AuthorizationCode("d" * 32)

    class SequencedGenerator:
        def __init__(self) -> None:
            self.codes = [first, second]

        def authorization_code(self) -> AuthorizationCode:
            return self.codes.pop(0)

        def access_token(self):
            raise AssertionError("token generation belongs to shared issuer")

    def create_result(record):
        if record.code == first:
            return AuthorizationCodeCreateCollision(code=first)
        return AuthorizationCodeStored(record=record)

    codes = FakeCodes(create_result=create_result)
    uow = FakeUow(codes)
    use_case = IssueAuthorizationCode(
        uow_factory=lambda: uow,
        generator=SequencedGenerator(),
        lifetime_policy=Lifetime180(),
        clock=lambda: NOW,
    )

    result = await use_case(SUBJECT, CLIENT, SCOPE)

    assert isinstance(result, AuthorizationCodeIssued)
    assert result.record.code == second
    assert [record.code for record in codes.created] == [first, second]
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_issue_authorization_code_collision_is_explicit_rejection_without_commit() -> None:
    codes = FakeCodes(create_result=AuthorizationCodeCreateCollision(code=CODE))
    uow = FakeUow(codes)
    use_case = IssueAuthorizationCode(
        uow_factory=lambda: uow,
        generator=FixedGenerator(),
        lifetime_policy=Lifetime180(),
        clock=lambda: NOW,
    )

    result = await use_case(SUBJECT, CLIENT, SCOPE)

    assert isinstance(result, AuthorizationCodeIssueRejected)
    assert result.reason is AuthorizationCodeIssueRejectReason.COLLISION
    assert uow.commits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("resolved", "reason"),
    [
        (AuthorizationCodeMissing(code=CODE), AuthorizationCodeExchangeRejectReason.NOT_FOUND),
        (
            AuthorizationCodeFound(record=code_record(client_id=ApiClientId("other"))),
            AuthorizationCodeExchangeRejectReason.CLIENT_MISMATCH,
        ),
        (
            AuthorizationCodeFound(record=code_record(expires_at=NOW - timedelta(seconds=1))),
            AuthorizationCodeExchangeRejectReason.EXPIRED,
        ),
    ],
)
async def test_exchange_rejects_missing_mismatched_or_expired_code_without_token_issue(
    resolved,
    reason,
) -> None:
    codes = FakeCodes(resolve_result=resolved)
    uow = FakeUow(codes)
    token_issuer = StubTokenIssuer(ApiTokenIssued(token=TOKEN, scope=SCOPE))
    use_case = ExchangeAuthorizationCode(
        uow_factory=lambda: uow,
        token_issuer=token_issuer,
        exchange_policy=FixedExchangePolicy(KeepAuthorizationCode()),
        clock=lambda: NOW,
    )

    result = await use_case(CODE, CLIENT)

    assert isinstance(result, AuthorizationCodeExchangeRejected)
    assert result.reason is reason
    assert token_issuer.calls == []
    assert uow.commits == 0


@pytest.mark.asyncio
async def test_exchange_at_exact_expiry_boundary_is_still_valid_and_keeps_code_in_legacy_mode() -> None:
    record = code_record(expires_at=NOW)
    codes = FakeCodes(resolve_result=AuthorizationCodeFound(record=record))
    uow = FakeUow(codes)
    token_issuer = StubTokenIssuer(ApiTokenIssued(token=TOKEN, scope=SCOPE))
    use_case = ExchangeAuthorizationCode(
        uow_factory=lambda: uow,
        token_issuer=token_issuer,
        exchange_policy=FixedExchangePolicy(KeepAuthorizationCode()),
        clock=lambda: NOW,
    )

    result = await use_case(CODE, CLIENT)

    assert isinstance(result, AuthorizationCodeExchanged)
    assert result.access_token == TOKEN
    assert result.scope == SCOPE
    assert codes.deleted == []
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_exchange_consume_policy_deletes_code_before_commit() -> None:
    record = code_record()
    codes = FakeCodes(
        resolve_result=AuthorizationCodeFound(record=record),
        delete_result=AuthorizationCodeDeleted(code=CODE),
    )
    uow = FakeUow(codes)
    token_issuer = StubTokenIssuer(ApiTokenIssued(token=TOKEN, scope=SCOPE))
    use_case = ExchangeAuthorizationCode(
        uow_factory=lambda: uow,
        token_issuer=token_issuer,
        exchange_policy=FixedExchangePolicy(ConsumeAuthorizationCode()),
        clock=lambda: NOW,
    )

    result = await use_case(CODE, CLIENT)

    assert isinstance(result, AuthorizationCodeExchanged)
    assert codes.deleted == [CODE]
    assert uow.commits == 1
