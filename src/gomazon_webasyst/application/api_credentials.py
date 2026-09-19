from collections.abc import Callable
from datetime import datetime

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.api_token_issuance import (
    ApiTokenIssueCollision,
    ApiTokenIssueConcurrentStateChanged,
    ApiTokenIssued,
    ApiTokenIssuer,
)
from gomazon_webasyst.application.ports.api_credential_generator import ApiCredentialGenerator
from gomazon_webasyst.application.ports.api_credential_policies import (
    AuthorizationCodeExchangePolicy,
    AuthorizationCodeLifetimePolicy,
    ConsumeAuthorizationCode,
    KeepAuthorizationCode,
)
from gomazon_webasyst.application.ports.api_credential_uow import ApiCredentialUnitOfWorkFactory
from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenAlreadyMissing,
    ApiTokenRevoked,
    ApiTokenTouchMissing,
    ApiTokenTouched,
    AuthorizationCodeAlreadyMissing,
    AuthorizationCodeCreateCollision,
    AuthorizationCodeFound,
    AuthorizationCodeMissing,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenAlreadyMissing,
    ApiAccessTokenIssueRejected,
    ApiAccessTokenIssueResult,
    ApiAccessTokenIssued,
    ApiAccessTokenResolveRejected,
    ApiAccessTokenResolveResult,
    ApiAccessTokenResolved,
    ApiAccessTokenRevocationResult,
    ApiAccessTokenRevoked,
    ApiTokenExpiresAt,
    ApiTokenLastUsedAt,
    ApiTokenMissing,
    ApiTokenResolved,
    AuthorizationCodeExchangeRejected,
    AuthorizationCodeExchangeResult,
    AuthorizationCodeExchanged,
    AuthorizationCodeIssueRejected,
    AuthorizationCodeIssueResult,
    AuthorizationCodeIssued,
    StoredAuthorizationCode,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    ApiAccessTokenIssueRejectReason,
    ApiAccessTokenResolveRejectReason,
    AuthorizationCodeExchangeRejectReason,
    AuthorizationCodeIssueRejectReason,
)


class IssueAuthorizationCode:
    def __init__(
        self,
        *,
        uow_factory: ApiCredentialUnitOfWorkFactory,
        generator: ApiCredentialGenerator,
        lifetime_policy: AuthorizationCodeLifetimePolicy,
        clock: Callable[[], datetime],
        max_generation_attempts: int = 3,
    ) -> None:
        if max_generation_attempts < 1:
            raise ValueError("max generation attempts must be positive")
        self._uow_factory = uow_factory
        self._generator = generator
        self._lifetime_policy = lifetime_policy
        self._clock = clock
        self._max_generation_attempts = max_generation_attempts

    async def __call__(
        self,
        subject: AuthenticatedSubject,
        client_id: ApiClientId,
        scope: ApiScope,
    ) -> AuthorizationCodeIssueResult:
        now = self._clock()
        expires_at = self._lifetime_policy.expires_at(now)
        async with self._uow_factory() as uow:
            for _ in range(self._max_generation_attempts):
                record = StoredAuthorizationCode(
                    code=self._generator.authorization_code(),
                    contact_id=subject.id,
                    client_id=client_id,
                    scope=scope,
                    expires_at=expires_at,
                )
                created = await uow.authorization_codes.create(record)
                if isinstance(created, AuthorizationCodeCreateCollision):
                    continue
                await uow.commit()
                return AuthorizationCodeIssued(record=record)
        return AuthorizationCodeIssueRejected(
            reason=AuthorizationCodeIssueRejectReason.COLLISION
        )


class ExchangeAuthorizationCode:
    def __init__(
        self,
        *,
        uow_factory: ApiCredentialUnitOfWorkFactory,
        token_issuer: ApiTokenIssuer,
        exchange_policy: AuthorizationCodeExchangePolicy,
        clock: Callable[[], datetime],
    ) -> None:
        self._uow_factory = uow_factory
        self._token_issuer = token_issuer
        self._exchange_policy = exchange_policy
        self._clock = clock

    async def __call__(
        self,
        code: AuthorizationCode,
        client_id: ApiClientId,
    ) -> AuthorizationCodeExchangeResult:
        async with self._uow_factory() as uow:
            resolved = await uow.authorization_codes.resolve(code)
            if isinstance(resolved, AuthorizationCodeMissing):
                return AuthorizationCodeExchangeRejected(
                    reason=AuthorizationCodeExchangeRejectReason.NOT_FOUND
                )

            if not isinstance(resolved, AuthorizationCodeFound):
                raise AssertionError("unsupported authorization code resolution")
            record = resolved.record
            if record.client_id != client_id:
                return AuthorizationCodeExchangeRejected(
                    reason=AuthorizationCodeExchangeRejectReason.CLIENT_MISMATCH
                )
            if record.expires_at < self._clock():
                return AuthorizationCodeExchangeRejected(
                    reason=AuthorizationCodeExchangeRejectReason.EXPIRED
                )

            issued = await self._token_issuer.issue(
                record.contact_id,
                record.client_id,
                record.scope,
                uow,
            )
            if isinstance(issued, ApiTokenIssueCollision):
                return AuthorizationCodeExchangeRejected(
                    reason=AuthorizationCodeExchangeRejectReason.TOKEN_COLLISION
                )
            if isinstance(issued, ApiTokenIssueConcurrentStateChanged):
                return AuthorizationCodeExchangeRejected(
                    reason=AuthorizationCodeExchangeRejectReason.CONCURRENT_STATE_CHANGED
                )
            if not isinstance(issued, ApiTokenIssued):
                raise AssertionError("unsupported api token issue result")

            disposition = self._exchange_policy.disposition()
            if isinstance(disposition, ConsumeAuthorizationCode):
                deleted = await uow.authorization_codes.delete(code)
                if isinstance(deleted, AuthorizationCodeAlreadyMissing):
                    return AuthorizationCodeExchangeRejected(
                        reason=AuthorizationCodeExchangeRejectReason.CODE_STATE_CHANGED
                    )
            elif not isinstance(disposition, KeepAuthorizationCode):
                raise AssertionError("unsupported authorization code exchange disposition")

            await uow.commit()
            return AuthorizationCodeExchanged(
                access_token=issued.token,
                scope=issued.scope,
            )


class IssueImplicitApiAccessToken:
    def __init__(
        self,
        *,
        uow_factory: ApiCredentialUnitOfWorkFactory,
        token_issuer: ApiTokenIssuer,
    ) -> None:
        self._uow_factory = uow_factory
        self._token_issuer = token_issuer

    async def __call__(
        self,
        subject: AuthenticatedSubject,
        client_id: ApiClientId,
        scope: ApiScope,
    ) -> ApiAccessTokenIssueResult:
        async with self._uow_factory() as uow:
            issued = await self._token_issuer.issue(subject.id, client_id, scope, uow)
            if isinstance(issued, ApiTokenIssueCollision):
                return ApiAccessTokenIssueRejected(
                    reason=ApiAccessTokenIssueRejectReason.TOKEN_COLLISION
                )
            if isinstance(issued, ApiTokenIssueConcurrentStateChanged):
                return ApiAccessTokenIssueRejected(
                    reason=ApiAccessTokenIssueRejectReason.CONCURRENT_STATE_CHANGED
                )
            if not isinstance(issued, ApiTokenIssued):
                raise AssertionError("unsupported api token issue result")
            await uow.commit()
            return ApiAccessTokenIssued(
                access_token=issued.token,
                scope=issued.scope,
            )


class ResolveApiAccessToken:
    def __init__(
        self,
        *,
        uow_factory: ApiCredentialUnitOfWorkFactory,
        clock: Callable[[], datetime],
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def __call__(self, token: ApiAccessToken) -> ApiAccessTokenResolveResult:
        async with self._uow_factory() as uow:
            resolved = await uow.tokens.resolve(token)
            if isinstance(resolved, ApiTokenMissing):
                return ApiAccessTokenResolveRejected(
                    reason=ApiAccessTokenResolveRejectReason.MISSING
                )
            if not isinstance(resolved, ApiTokenResolved):
                raise AssertionError("unsupported api token resolution")

            record = resolved.record
            now = self._clock()
            if isinstance(record.expiry, ApiTokenExpiresAt) and record.expiry.at < now:
                return ApiAccessTokenResolveRejected(
                    reason=ApiAccessTokenResolveRejectReason.EXPIRED
                )

            touched = await uow.tokens.touch_last_use(token, now)
            if isinstance(touched, ApiTokenTouchMissing):
                return ApiAccessTokenResolveRejected(
                    reason=ApiAccessTokenResolveRejectReason.CONCURRENT_STATE_CHANGED
                )
            if not isinstance(touched, ApiTokenTouched):
                raise AssertionError("unsupported api token touch result")

            await uow.commit()
            return ApiAccessTokenResolved(
                access_token=record.token,
                contact_id=record.contact_id,
                client_id=record.client_id,
                scope=record.scope,
                last_use=ApiTokenLastUsedAt(at=now),
            )


class RevokeApiAccessToken:
    def __init__(self, *, uow_factory: ApiCredentialUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def __call__(self, token: ApiAccessToken) -> ApiAccessTokenRevocationResult:
        async with self._uow_factory() as uow:
            revoked = await uow.tokens.revoke(token)
            if isinstance(revoked, ApiTokenAlreadyMissing):
                return ApiAccessTokenAlreadyMissing(access_token=token)
            if not isinstance(revoked, ApiTokenRevoked):
                raise AssertionError("unsupported api token revocation result")
            await uow.commit()
            return ApiAccessTokenRevoked(access_token=token)
