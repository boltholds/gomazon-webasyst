from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.application.auth_values import AuthSessionKey
from gomazon_webasyst.application.persistent_values import (
    PersistentCredential,
    PersistentCredentialLifetime,
)
from gomazon_webasyst.contracts.auth import AuthIdentity, AuthenticatedSubject, SessionMetadata
from gomazon_webasyst.contracts.enums import (
    BackendSessionEstablishmentKind,
    BackendSessionEstablishmentRejectReason,
    PersistentCredentialDispositionKind,
    PersistentCredentialIssueKind,
    PersistentCredentialIssueRejectReason,
    PersistentCredentialRejectReason,
    PersistentCredentialResolutionKind,
    PersistentLoginRejectReason,
    PersistentLoginResultKind,
    PersistentStrategyResultKind,
)


class RefreshPersistentCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[PersistentCredentialDispositionKind.REFRESH] = PersistentCredentialDispositionKind.REFRESH
    credential: PersistentCredential
    lifetime: PersistentCredentialLifetime


class ClearPersistentCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentCredentialDispositionKind.CLEAR] = PersistentCredentialDispositionKind.CLEAR


class KeepPersistentCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentCredentialDispositionKind.KEEP] = PersistentCredentialDispositionKind.KEEP


PersistentCredentialDisposition: TypeAlias = Annotated[
    RefreshPersistentCredential | ClearPersistentCredential | KeepPersistentCredential,
    Field(discriminator="kind"),
]


class PersistentStrategyResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentStrategyResultKind.RESOLVED] = PersistentStrategyResultKind.RESOLVED
    identity: AuthIdentity
    disposition: PersistentCredentialDisposition


class PersistentStrategyNotApplicable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentStrategyResultKind.NOT_APPLICABLE] = PersistentStrategyResultKind.NOT_APPLICABLE


class PersistentStrategyRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentStrategyResultKind.REJECTED] = PersistentStrategyResultKind.REJECTED
    reason: PersistentCredentialRejectReason
    disposition: PersistentCredentialDisposition


PersistentCredentialStrategyResult: TypeAlias = Annotated[
    PersistentStrategyResolved | PersistentStrategyNotApplicable | PersistentStrategyRejected,
    Field(discriminator="kind"),
]


class PersistentCredentialResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentCredentialResolutionKind.RESOLVED] = PersistentCredentialResolutionKind.RESOLVED
    identity: AuthIdentity
    disposition: PersistentCredentialDisposition


class PersistentCredentialRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentCredentialResolutionKind.REJECTED] = PersistentCredentialResolutionKind.REJECTED
    reason: PersistentCredentialRejectReason
    disposition: PersistentCredentialDisposition


PersistentCredentialResolution: TypeAlias = Annotated[
    PersistentCredentialResolved | PersistentCredentialRejected,
    Field(discriminator="kind"),
]


class PersistentCredentialIssued(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[PersistentCredentialIssueKind.ISSUED] = PersistentCredentialIssueKind.ISSUED
    credential: PersistentCredential
    lifetime: PersistentCredentialLifetime


class PersistentCredentialIssueRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentCredentialIssueKind.REJECTED] = PersistentCredentialIssueKind.REJECTED
    reason: PersistentCredentialIssueRejectReason


PersistentCredentialIssueResult: TypeAlias = Annotated[
    PersistentCredentialIssued | PersistentCredentialIssueRejected,
    Field(discriminator="kind"),
]


class BackendSessionEstablished(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[BackendSessionEstablishmentKind.ESTABLISHED] = BackendSessionEstablishmentKind.ESTABLISHED
    subject: AuthenticatedSubject
    session_key: AuthSessionKey


class BackendSessionEstablishmentRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[BackendSessionEstablishmentKind.REJECTED] = BackendSessionEstablishmentKind.REJECTED
    reason: BackendSessionEstablishmentRejectReason


BackendSessionEstablishmentResult: TypeAlias = Annotated[
    BackendSessionEstablished | BackendSessionEstablishmentRejected,
    Field(discriminator="kind"),
]


class PersistentLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    credential: PersistentCredential
    session_metadata: SessionMetadata = Field(default_factory=SessionMetadata)


class PersistentLoginRestored(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[PersistentLoginResultKind.RESTORED] = PersistentLoginResultKind.RESTORED
    subject: AuthenticatedSubject
    session_key: AuthSessionKey
    credential_disposition: PersistentCredentialDisposition


class PersistentLoginRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PersistentLoginResultKind.REJECTED] = PersistentLoginResultKind.REJECTED
    reason: PersistentLoginRejectReason
    credential_disposition: PersistentCredentialDisposition


PersistentLoginResult: TypeAlias = Annotated[
    PersistentLoginRestored | PersistentLoginRejected,
    Field(discriminator="kind"),
]
