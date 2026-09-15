from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
)
from gomazon_webasyst.application.ports.api_credential_generator import ApiCredentialGenerator
from gomazon_webasyst.application.ports.api_credential_policies import (
    ApiTokenIssuePolicy,
    ReuseApiToken,
    ReuseApiTokenWithScopeUpdate,
)
from gomazon_webasyst.application.ports.api_credential_uow import ApiCredentialUnitOfWork
from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenForSubjectClientFound,
    ApiTokenForSubjectClientMissing,
    ApiTokenScopeUpdateMissing,
    ApiTokenScopeUpdated,
    ApiTokenStored,
    ApiTokenSubjectClientCollision,
    ApiTokenValueCollision,
)
from gomazon_webasyst.contracts.api_credentials import ApiTokenNeverUsed, StoredApiAccessToken


@dataclass(slots=True, frozen=True)
class ApiTokenIssued:
    token: ApiAccessToken
    scope: ApiScope


@dataclass(slots=True, frozen=True)
class ApiTokenIssueCollision:
    token: ApiAccessToken


@dataclass(slots=True, frozen=True)
class ApiTokenIssueConcurrentStateChanged:
    contact_id: int
    client_id: ApiClientId


ApiTokenIssueResult: TypeAlias = (
    ApiTokenIssued | ApiTokenIssueCollision | ApiTokenIssueConcurrentStateChanged
)


class ApiTokenIssuer:
    def __init__(
        self,
        *,
        generator: ApiCredentialGenerator,
        issue_policy: ApiTokenIssuePolicy,
        clock: Callable[[], datetime],
    ) -> None:
        self._generator = generator
        self._issue_policy = issue_policy
        self._clock = clock

    async def issue(
        self,
        contact_id: int,
        client_id: ApiClientId,
        scope: ApiScope,
        uow: ApiCredentialUnitOfWork,
    ) -> ApiTokenIssueResult:
        current = await uow.tokens.find_for_subject_client(contact_id, client_id)
        if isinstance(current, ApiTokenForSubjectClientFound):
            return await self._reuse(current.record, scope, uow)
        return await self._create(contact_id, client_id, scope, uow)

    async def _reuse(
        self,
        record: StoredApiAccessToken,
        requested_scope: ApiScope,
        uow: ApiCredentialUnitOfWork,
    ) -> ApiTokenIssueResult:
        plan = self._issue_policy.for_existing(record.scope, requested_scope)
        if isinstance(plan, ReuseApiToken):
            return ApiTokenIssued(token=record.token, scope=record.scope)
        if isinstance(plan, ReuseApiTokenWithScopeUpdate):
            update = await uow.tokens.update_scope(record.token, plan.scope)
            if isinstance(update, ApiTokenScopeUpdated):
                return ApiTokenIssued(token=record.token, scope=plan.scope)
            if isinstance(update, ApiTokenScopeUpdateMissing):
                return await self._create(
                    record.contact_id,
                    record.client_id,
                    requested_scope,
                    uow,
                )
        raise AssertionError("unsupported api token issue plan")

    async def _create(
        self,
        contact_id: int,
        client_id: ApiClientId,
        scope: ApiScope,
        uow: ApiCredentialUnitOfWork,
    ) -> ApiTokenIssueResult:
        plan = self._issue_policy.for_missing()
        token = self._generator.access_token()
        record = StoredApiAccessToken(
            token=token,
            contact_id=contact_id,
            client_id=client_id,
            scope=scope,
            created_at=self._clock(),
            last_use=ApiTokenNeverUsed(),
            expiry=plan.expiry,
        )
        created = await uow.tokens.create(record)
        if isinstance(created, ApiTokenStored):
            return ApiTokenIssued(token=token, scope=scope)
        if isinstance(created, ApiTokenValueCollision):
            return ApiTokenIssueCollision(token=created.token)
        if isinstance(created, ApiTokenSubjectClientCollision):
            winner = await uow.tokens.find_for_subject_client(contact_id, client_id)
            if isinstance(winner, ApiTokenForSubjectClientFound):
                return await self._reuse(winner.record, scope, uow)
            if isinstance(winner, ApiTokenForSubjectClientMissing):
                return ApiTokenIssueConcurrentStateChanged(
                    contact_id=contact_id,
                    client_id=client_id,
                )
        raise AssertionError("unsupported api token create result")
