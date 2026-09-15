from gomazon_webasyst.application.ports.auth_subjects import AuthSubjectStore
from gomazon_webasyst.application.ports.persistent_credentials import (
    PersistentCredentialIssuer,
    PersistentCredentialResolver,
)
from gomazon_webasyst.application.session_establishment import BackendSessionEstablisher
from gomazon_webasyst.contracts.auth import AuthenticatedSubject, SubjectResolutionError
from gomazon_webasyst.contracts.enums import (
    PersistentCredentialIssueRejectReason,
    PersistentLoginRejectReason,
    SubjectResolutionErrorType,
)
from gomazon_webasyst.contracts.persistent_login import (
    BackendSessionEstablishmentRejected,
    KeepPersistentCredential,
    PersistentCredentialIssueRejected,
    PersistentCredentialIssueResult,
    PersistentCredentialRejected,
    PersistentLoginRejected,
    PersistentLoginRequest,
    PersistentLoginRestored,
    PersistentLoginResult,
)


class IssuePersistentCredential:
    def __init__(
        self,
        *,
        subject_store: AuthSubjectStore,
        issuer: PersistentCredentialIssuer,
    ) -> None:
        self._subject_store = subject_store
        self._issuer = issuer

    async def __call__(
        self,
        subject: AuthenticatedSubject,
    ) -> PersistentCredentialIssueResult:
        subject_result = await self._subject_store.get(subject.id)
        if isinstance(subject_result, SubjectResolutionError):
            reason = (
                PersistentCredentialIssueRejectReason.SUBJECT_NOT_FOUND
                if subject_result.type is SubjectResolutionErrorType.NOT_FOUND
                else PersistentCredentialIssueRejectReason.SUBJECT_DISABLED
            )
            return PersistentCredentialIssueRejected(reason=reason)

        return await self._issuer.issue(subject_result.identity)


class RestoreBackendSessionFromPersistentCredential:
    def __init__(
        self,
        *,
        resolver: PersistentCredentialResolver,
        session_establisher: BackendSessionEstablisher,
    ) -> None:
        self._resolver = resolver
        self._session_establisher = session_establisher

    async def __call__(self, request: PersistentLoginRequest) -> PersistentLoginResult:
        resolved = await self._resolver.resolve(request.credential)
        if isinstance(resolved, PersistentCredentialRejected):
            return PersistentLoginRejected(
                reason=PersistentLoginRejectReason.CREDENTIAL_REJECTED,
                credential_disposition=resolved.disposition,
            )

        established = await self._session_establisher.establish(
            resolved.identity,
            request.session_metadata,
        )
        if isinstance(established, BackendSessionEstablishmentRejected):
            return PersistentLoginRejected(
                reason=PersistentLoginRejectReason.SESSION_UNAVAILABLE,
                credential_disposition=KeepPersistentCredential(),
            )

        return PersistentLoginRestored(
            subject=established.subject,
            session_key=established.session_key,
            credential_disposition=resolved.disposition,
        )
