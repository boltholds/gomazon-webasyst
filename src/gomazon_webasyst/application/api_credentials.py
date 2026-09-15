from collections.abc import Callable
from datetime import datetime

from gomazon_webasyst.application.api_credential_values import (
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
    AuthorizationCodeAlreadyMissing,
    AuthorizationCodeCreateCollision,
    AuthorizationCodeFound,
    AuthorizationCodeMissing,
)
from gomazon_webasyst.contracts.api_credentials import (
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
    ) -> None:
        self._uow_factory = uow_factory
        self._generator = generator
        self._lifetime_policy = lifetime_policy
        self._clock = clock

    async def __call__(
        self,
        subject: AuthenticatedSubject,
        client_id: ApiClientId,
        scope: ApiScope,
    ) -> AuthorizationCodeIssueResult:
        now = self._clock()
        record = StoredAuthorizationCode(
            code=self._generator.authorization_code(),
            contact_id=subject.id,
            client_id=client_id,
            scope=scope,
            expires_at=self._lifetime_policy.expires_at(now),
        )
        async with self._uow_factory() as uow:
            created = await uow.authorization_codes.create(record)
            if isinstance(created, AuthorizationCodeCreateCollision):
                return AuthorizationCodeIssueRejected(
                    reason=AuthorizationCodeIssueRejectReason.COLLISION
                )
            await uow.commit()
        return AuthorizationCodeIssued(record=record)


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
