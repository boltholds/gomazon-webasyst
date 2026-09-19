from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    AuthenticationRejectType,
    BackendLoginPersistenceStatus,
    BackendLogoutKind,
    BackendPasswordLoginKind,
    CurrentBackendSubjectKind,
    CurrentBackendSubjectReason,
    LogoutStatus,
    SessionCredentialDispositionKind,
)
from gomazon_webasyst.contracts.persistent_login import (
    PersistentCredentialDisposition,
)


class IssueSessionCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[SessionCredentialDispositionKind.ISSUE] = (
        SessionCredentialDispositionKind.ISSUE
    )
    session_id: SessionId


class ClearSessionCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SessionCredentialDispositionKind.CLEAR] = (
        SessionCredentialDispositionKind.CLEAR
    )


class KeepSessionCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SessionCredentialDispositionKind.KEEP] = (
        SessionCredentialDispositionKind.KEEP
    )


SessionCredentialDisposition: TypeAlias = Annotated[
    IssueSessionCredential | ClearSessionCredential | KeepSessionCredential,
    Field(discriminator="kind"),
]


class CurrentBackendSubjectResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[CurrentBackendSubjectKind.RESOLVED] = CurrentBackendSubjectKind.RESOLVED
    subject: AuthenticatedSubject
    session_disposition: SessionCredentialDisposition
    persistent_disposition: PersistentCredentialDisposition


class CurrentBackendSubjectUnauthenticated(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[CurrentBackendSubjectKind.UNAUTHENTICATED] = (
        CurrentBackendSubjectKind.UNAUTHENTICATED
    )
    reason: CurrentBackendSubjectReason
    session_disposition: SessionCredentialDisposition
    persistent_disposition: PersistentCredentialDisposition


CurrentBackendSubjectResult: TypeAlias = Annotated[
    CurrentBackendSubjectResolved | CurrentBackendSubjectUnauthenticated,
    Field(discriminator="kind"),
]


class BackendPasswordLoginSucceeded(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[BackendPasswordLoginKind.SUCCEEDED] = (
        BackendPasswordLoginKind.SUCCEEDED
    )
    subject: AuthenticatedSubject
    session_disposition: SessionCredentialDisposition
    persistent_disposition: PersistentCredentialDisposition
    persistence_status: BackendLoginPersistenceStatus


class BackendPasswordLoginRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[BackendPasswordLoginKind.REJECTED] = BackendPasswordLoginKind.REJECTED
    authentication_type: AuthenticationRejectType
    session_disposition: SessionCredentialDisposition
    persistent_disposition: PersistentCredentialDisposition


BackendPasswordLoginResult: TypeAlias = Annotated[
    BackendPasswordLoginSucceeded | BackendPasswordLoginRejected,
    Field(discriminator="kind"),
]


class BackendLogoutCompleted(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[BackendLogoutKind.COMPLETED] = BackendLogoutKind.COMPLETED
    session_status: LogoutStatus
    session_disposition: SessionCredentialDisposition
    persistent_disposition: PersistentCredentialDisposition


BackendLogoutResult: TypeAlias = BackendLogoutCompleted
