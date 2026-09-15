from dataclasses import dataclass
from datetime import timedelta
from hmac import compare_digest
import re
from typing import TypeAlias

from gomazon_webasyst.application.persistent_values import (
    PersistentCredential,
    PersistentCredentialLifetime,
)
from gomazon_webasyst.application.ports.auth_subjects import AuthSubjectStore
from gomazon_webasyst.application.ports.credential_tokens import CredentialVersionTokenFactory
from gomazon_webasyst.contracts.auth import AuthIdentity, SubjectResolutionError
from gomazon_webasyst.contracts.enums import (
    PersistentCredentialRejectReason,
    SubjectResolutionErrorType,
)
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    PersistentCredentialIssued,
    PersistentCredentialIssueResult,
    PersistentCredentialStrategyResult,
    PersistentStrategyRejected,
    PersistentStrategyResolved,
    RefreshPersistentCredential,
)


LEGACY_AUTH_TOKEN_LIFETIME = PersistentCredentialLifetime(timedelta(days=30))
_LEGACY_AUTH_TOKEN_PATTERN = re.compile(r"^[0-9a-fA-F]{15}([0-9]+)[0-9a-fA-F]{15}$")


@dataclass(slots=True, frozen=True)
class LegacyAuthTokenCredential:
    contact_id: int
    credential: PersistentCredential


@dataclass(slots=True, frozen=True)
class LegacyTokenParsed:
    credential: LegacyAuthTokenCredential


@dataclass(slots=True, frozen=True)
class LegacyTokenMalformed:
    pass


LegacyTokenParseResult: TypeAlias = LegacyTokenParsed | LegacyTokenMalformed


class LegacyAuthTokenParser:
    def parse(self, credential: PersistentCredential) -> LegacyTokenParseResult:
        match = _LEGACY_AUTH_TOKEN_PATTERN.fullmatch(credential.value)
        if match is None:
            return LegacyTokenMalformed()
        return LegacyTokenParsed(
            credential=LegacyAuthTokenCredential(
                contact_id=int(match.group(1)),
                credential=credential,
            )
        )


class LegacyAuthTokenStrategy:
    def __init__(
        self,
        *,
        subject_store: AuthSubjectStore,
        token_factory: CredentialVersionTokenFactory,
        parser: LegacyAuthTokenParser = LegacyAuthTokenParser(),
        lifetime: PersistentCredentialLifetime = LEGACY_AUTH_TOKEN_LIFETIME,
    ) -> None:
        self._subject_store = subject_store
        self._token_factory = token_factory
        self._parser = parser
        self._lifetime = lifetime

    async def resolve(
        self,
        credential: PersistentCredential,
    ) -> PersistentCredentialStrategyResult:
        parsed = self._parser.parse(credential)
        if isinstance(parsed, LegacyTokenMalformed):
            return PersistentStrategyRejected(
                reason=PersistentCredentialRejectReason.MALFORMED,
                disposition=ClearPersistentCredential(),
            )

        subject_result = await self._subject_store.get(parsed.credential.contact_id)
        if isinstance(subject_result, SubjectResolutionError):
            reason = (
                PersistentCredentialRejectReason.SUBJECT_NOT_FOUND
                if subject_result.type is SubjectResolutionErrorType.NOT_FOUND
                else PersistentCredentialRejectReason.SUBJECT_DISABLED
            )
            return PersistentStrategyRejected(
                reason=reason,
                disposition=ClearPersistentCredential(),
            )

        expected = self._token_factory.create(subject_result.identity)
        if not compare_digest(credential.value, expected):
            return PersistentStrategyRejected(
                reason=PersistentCredentialRejectReason.INVALID,
                disposition=ClearPersistentCredential(),
            )

        return PersistentStrategyResolved(
            identity=subject_result.identity,
            disposition=RefreshPersistentCredential(
                credential=credential,
                lifetime=self._lifetime,
            ),
        )


class LegacyAuthTokenIssuer:
    def __init__(
        self,
        token_factory: CredentialVersionTokenFactory,
        lifetime: PersistentCredentialLifetime = LEGACY_AUTH_TOKEN_LIFETIME,
    ) -> None:
        self._token_factory = token_factory
        self._lifetime = lifetime

    async def issue(self, identity: AuthIdentity) -> PersistentCredentialIssueResult:
        return PersistentCredentialIssued(
            credential=PersistentCredential(self._token_factory.create(identity)),
            lifetime=self._lifetime,
        )
