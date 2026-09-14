from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from gomazon_webasyst.application.auth_values import AuthSessionKey
from gomazon_webasyst.contracts.enums import (
    AuthenticationRejectType,
    AuthenticationResultKind,
    IdentityKeyResolutionKind,
    IdentityResolutionErrorType,
    IdentityResolutionKind,
    LoginPlanErrorType,
    LoginPlanKind,
    LoginPolicyDecisionKind,
    LoginPolicyRejectType,
    LogoutStatus,
    PasswordVerificationErrorType,
    PasswordVerificationKind,
    RegistryCheckKind,
    RegistryRevocationKind,
    RegistryTouchKind,
    RegistryWriteKind,
    SessionCreationErrorType,
    SessionCreationKind,
    SessionResolutionErrorType,
    SessionResolutionKind,
    SessionRevocationKind,
    SessionStateErrorType,
    SessionStateResolutionKind,
    SubjectResolutionErrorType,
    SubjectResolutionKind,
)


class AuthIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    login: str
    password_hash: str
    is_user: int
    create_datetime: datetime


class IdentityKey(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scheme: str
    value: str


class IdentityLookupPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    keys: tuple[IdentityKey, ...]


class IdentityResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[IdentityResolutionKind.RESOLVED] = IdentityResolutionKind.RESOLVED
    identity: AuthIdentity
    matched_key: IdentityKey


class IdentityResolutionError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[IdentityResolutionKind.ERROR] = IdentityResolutionKind.ERROR
    type: IdentityResolutionErrorType


IdentityResolution: TypeAlias = Annotated[
    IdentityResolved | IdentityResolutionError,
    Field(discriminator="kind"),
]


class PasswordAccepted(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PasswordVerificationKind.ACCEPTED] = PasswordVerificationKind.ACCEPTED


class PasswordVerificationError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PasswordVerificationKind.ERROR] = PasswordVerificationKind.ERROR
    type: PasswordVerificationErrorType


PasswordVerification: TypeAlias = Annotated[
    PasswordAccepted | PasswordVerificationError,
    Field(discriminator="kind"),
]


class AuthenticatedSubject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    login: str


class SubjectResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SubjectResolutionKind.RESOLVED] = SubjectResolutionKind.RESOLVED
    identity: AuthIdentity


class SubjectResolutionError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SubjectResolutionKind.ERROR] = SubjectResolutionKind.ERROR
    type: SubjectResolutionErrorType


SubjectResolution: TypeAlias = Annotated[
    SubjectResolved | SubjectResolutionError,
    Field(discriminator="kind"),
]


class SessionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_agent: str = ""


class AuthSessionRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    key: AuthSessionKey
    credential_token: str
    user_agent: str = ""


class AuthenticationSucceeded(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[AuthenticationResultKind.SUCCEEDED] = AuthenticationResultKind.SUCCEEDED
    subject: AuthenticatedSubject
    session_key: AuthSessionKey


class AuthenticationRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AuthenticationResultKind.REJECTED] = AuthenticationResultKind.REJECTED
    type: AuthenticationRejectType


AuthenticationResult: TypeAlias = Annotated[
    AuthenticationSucceeded | AuthenticationRejected,
    Field(discriminator="kind"),
]


class SessionResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[SessionResolutionKind.RESOLVED] = SessionResolutionKind.RESOLVED
    subject: AuthenticatedSubject
    session_key: AuthSessionKey


class SessionResolutionError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SessionResolutionKind.ERROR] = SessionResolutionKind.ERROR
    type: SessionResolutionErrorType


SessionResolutionResult: TypeAlias = Annotated[
    SessionResolved | SessionResolutionError,
    Field(discriminator="kind"),
]


class LoginPolicyContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled_schemes: tuple[str, ...]


class PolicyContribute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LoginPolicyDecisionKind.CONTRIBUTE] = LoginPolicyDecisionKind.CONTRIBUTE
    keys: tuple[IdentityKey, ...]


class PolicySkip(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LoginPolicyDecisionKind.SKIP] = LoginPolicyDecisionKind.SKIP


class PolicyReject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LoginPolicyDecisionKind.REJECT] = LoginPolicyDecisionKind.REJECT
    type: LoginPolicyRejectType


LoginPolicyDecision: TypeAlias = Annotated[
    PolicyContribute | PolicySkip | PolicyReject,
    Field(discriminator="kind"),
]


class LoginPlanBuilt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LoginPlanKind.PLANNED] = LoginPlanKind.PLANNED
    plan: IdentityLookupPlan


class LoginPlanError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LoginPlanKind.ERROR] = LoginPlanKind.ERROR
    type: LoginPlanErrorType


LoginPlanResult: TypeAlias = Annotated[
    LoginPlanBuilt | LoginPlanError,
    Field(discriminator="kind"),
]


class IdentityKeyResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[IdentityKeyResolutionKind.RESOLVED] = IdentityKeyResolutionKind.RESOLVED
    identity: AuthIdentity


class IdentityKeyNotFound(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[IdentityKeyResolutionKind.NOT_FOUND] = IdentityKeyResolutionKind.NOT_FOUND


IdentityKeyResolution: TypeAlias = Annotated[
    IdentityKeyResolved | IdentityKeyNotFound,
    Field(discriminator="kind"),
]


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: AuthenticatedSubject
    credential_token: str
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)


class StoredAuthSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    key: AuthSessionKey
    subject: AuthenticatedSubject
    credential_token: str
    metadata: SessionMetadata
    created_at: datetime
    last_seen_at: datetime


class SessionCreated(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[SessionCreationKind.CREATED] = SessionCreationKind.CREATED
    state: StoredAuthSession


class SessionCreationError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SessionCreationKind.ERROR] = SessionCreationKind.ERROR
    type: SessionCreationErrorType


SessionCreationResult: TypeAlias = Annotated[
    SessionCreated | SessionCreationError,
    Field(discriminator="kind"),
]


class SessionStateResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[SessionStateResolutionKind.RESOLVED] = SessionStateResolutionKind.RESOLVED
    state: StoredAuthSession


class SessionStateError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SessionStateResolutionKind.ERROR] = SessionStateResolutionKind.ERROR
    type: SessionStateErrorType


SessionStateResolution: TypeAlias = Annotated[
    SessionStateResolved | SessionStateError,
    Field(discriminator="kind"),
]


class SessionRevoked(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SessionRevocationKind.REVOKED] = SessionRevocationKind.REVOKED


class SessionAlreadyMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SessionRevocationKind.ALREADY_MISSING] = SessionRevocationKind.ALREADY_MISSING


SessionRevocationResult: TypeAlias = Annotated[
    SessionRevoked | SessionAlreadyMissing,
    Field(discriminator="kind"),
]


class RegistryWritten(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RegistryWriteKind.WRITTEN] = RegistryWriteKind.WRITTEN


class RegistryActive(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RegistryCheckKind.ACTIVE] = RegistryCheckKind.ACTIVE


class RegistryMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RegistryCheckKind.MISSING] = RegistryCheckKind.MISSING


RegistryCheckResult: TypeAlias = Annotated[
    RegistryActive | RegistryMissing,
    Field(discriminator="kind"),
]


class RegistryTouched(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RegistryTouchKind.TOUCHED] = RegistryTouchKind.TOUCHED


class RegistryTouchMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RegistryTouchKind.MISSING] = RegistryTouchKind.MISSING


RegistryTouchResult: TypeAlias = Annotated[
    RegistryTouched | RegistryTouchMissing,
    Field(discriminator="kind"),
]


class RegistryRevoked(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RegistryRevocationKind.REVOKED] = RegistryRevocationKind.REVOKED


class RegistryAlreadyMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RegistryRevocationKind.ALREADY_MISSING] = RegistryRevocationKind.ALREADY_MISSING


RegistryRevocationResult: TypeAlias = Annotated[
    RegistryRevoked | RegistryAlreadyMissing,
    Field(discriminator="kind"),
]


class BackendPasswordCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    identifier: str
    password: SecretStr
    login_context: LoginPolicyContext
    session_metadata: SessionMetadata = Field(default_factory=SessionMetadata)


class LogoutResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: LogoutStatus
