from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.auth import (
    AuthenticateBackendPassword,
    LogoutBackendSession,
    ResolveBackendSession,
)
from gomazon_webasyst.application.persistent_login import (
    IssuePersistentCredential,
    RestoreBackendSessionFromPersistentCredential,
    RevokePersistentCredential,
)
from gomazon_webasyst.application.ports.auth_session_registry import AuthSessionRegistry
from gomazon_webasyst.application.ports.auth_subjects import AuthSubjectStore
from gomazon_webasyst.application.ports.credential_tokens import CredentialVersionTokenFactory
from gomazon_webasyst.application.ports.identity_directory import IdentityDirectory
from gomazon_webasyst.application.ports.login_policy import LoginPlanner
from gomazon_webasyst.application.ports.password_verifier import PasswordVerifier
from gomazon_webasyst.application.ports.persistent_credentials import (
    PersistentCredentialIssuer,
    PersistentCredentialResolver,
)
from gomazon_webasyst.application.ports.session_state import SessionStateStore
from gomazon_webasyst.application.ports.session_validation import (
    SessionValidationPolicy,
    StrictSessionValidationPolicy,
)
from gomazon_webasyst.application.session_establishment import BackendSessionEstablisher
from gomazon_webasyst.compatibility.webasyst.auth.factory import create_webasyst_login_policy_set
from gomazon_webasyst.compatibility.webasyst.auth.passwords import LegacyMd5PasswordVerifier
from gomazon_webasyst.compatibility.webasyst.auth.persistent import (
    LegacyAuthTokenIssuer,
    LegacyAuthTokenStrategy,
)
from gomazon_webasyst.compatibility.webasyst.auth.phone import LegacyPhonePrefixPolicy
from gomazon_webasyst.compatibility.webasyst.auth.tokens import LegacyCredentialVersionTokenFactory
from gomazon_webasyst.infrastructure.auth.identity_directory import create_sqlalchemy_identity_directory
from gomazon_webasyst.infrastructure.auth.persistent_credentials import OrderedPersistentCredentialResolver
from gomazon_webasyst.infrastructure.auth.session_registry import SQLAlchemyAuthSessionRegistry
from gomazon_webasyst.infrastructure.auth.subjects import SQLAlchemyAuthSubjectStore


@dataclass(slots=True, frozen=True)
class AuthUseCases:
    authenticate_backend_password: AuthenticateBackendPassword
    resolve_backend_session: ResolveBackendSession
    logout_backend_session: LogoutBackendSession
    issue_persistent_credential: IssuePersistentCredential
    restore_backend_session_from_persistent_credential: RestoreBackendSessionFromPersistentCredential
    revoke_persistent_credential: RevokePersistentCredential


@dataclass(slots=True, frozen=True)
class _AuthFoundation:
    planner: LoginPlanner
    identity_directory: IdentityDirectory
    subject_store: AuthSubjectStore
    password_verifier: PasswordVerifier
    token_factory: CredentialVersionTokenFactory
    session_state: SessionStateStore
    session_registry: AuthSessionRegistry
    session_establisher: BackendSessionEstablisher


def _create_auth_foundation(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_state: SessionStateStore,
    phone_prefix_policy: LegacyPhonePrefixPolicy,
) -> _AuthFoundation:
    planner = create_webasyst_login_policy_set()
    directory = create_sqlalchemy_identity_directory(
        session_factory,
        phone_candidates=phone_prefix_policy.candidates,
    )
    subjects = SQLAlchemyAuthSubjectStore(session_factory)
    verifier = LegacyMd5PasswordVerifier()
    token_factory = LegacyCredentialVersionTokenFactory()
    registry = SQLAlchemyAuthSessionRegistry(session_factory)
    establisher = BackendSessionEstablisher(
        session_state=session_state,
        session_registry=registry,
        token_factory=token_factory,
    )
    return _AuthFoundation(
        planner=planner,
        identity_directory=directory,
        subject_store=subjects,
        password_verifier=verifier,
        token_factory=token_factory,
        session_state=session_state,
        session_registry=registry,
        session_establisher=establisher,
    )


def _assemble_auth_use_cases(
    foundation: _AuthFoundation,
    *,
    persistent_resolver: PersistentCredentialResolver,
    persistent_issuer: PersistentCredentialIssuer,
    validation_policy: SessionValidationPolicy,
) -> AuthUseCases:
    return AuthUseCases(
        authenticate_backend_password=AuthenticateBackendPassword(
            planner=foundation.planner,
            identity_directory=foundation.identity_directory,
            password_verifier=foundation.password_verifier,
            session_establisher=foundation.session_establisher,
        ),
        resolve_backend_session=ResolveBackendSession(
            session_state=foundation.session_state,
            subject_store=foundation.subject_store,
            token_factory=foundation.token_factory,
            session_registry=foundation.session_registry,
            validation_policy=validation_policy,
        ),
        logout_backend_session=LogoutBackendSession(
            session_state=foundation.session_state,
            session_registry=foundation.session_registry,
        ),
        issue_persistent_credential=IssuePersistentCredential(
            subject_store=foundation.subject_store,
            issuer=persistent_issuer,
        ),
        restore_backend_session_from_persistent_credential=(
            RestoreBackendSessionFromPersistentCredential(
                resolver=persistent_resolver,
                session_establisher=foundation.session_establisher,
            )
        ),
        revoke_persistent_credential=RevokePersistentCredential(),
    )


def create_auth_use_cases(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_state: SessionStateStore,
    phone_prefix_policy: LegacyPhonePrefixPolicy = LegacyPhonePrefixPolicy(),
    validation_policy: SessionValidationPolicy = StrictSessionValidationPolicy(),
) -> AuthUseCases:
    foundation = _create_auth_foundation(
        session_factory,
        session_state=session_state,
        phone_prefix_policy=phone_prefix_policy,
    )
    legacy_strategy = LegacyAuthTokenStrategy(
        subject_store=foundation.subject_store,
        token_factory=foundation.token_factory,
    )
    resolver = OrderedPersistentCredentialResolver((legacy_strategy,))
    issuer = LegacyAuthTokenIssuer(foundation.token_factory)
    return _assemble_auth_use_cases(
        foundation,
        persistent_resolver=resolver,
        persistent_issuer=issuer,
        validation_policy=validation_policy,
    )


def create_auth_use_cases_with_persistent_credentials(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_state: SessionStateStore,
    persistent_resolver: PersistentCredentialResolver,
    persistent_issuer: PersistentCredentialIssuer,
    phone_prefix_policy: LegacyPhonePrefixPolicy = LegacyPhonePrefixPolicy(),
    validation_policy: SessionValidationPolicy = StrictSessionValidationPolicy(),
) -> AuthUseCases:
    foundation = _create_auth_foundation(
        session_factory,
        session_state=session_state,
        phone_prefix_policy=phone_prefix_policy,
    )
    return _assemble_auth_use_cases(
        foundation,
        persistent_resolver=persistent_resolver,
        persistent_issuer=persistent_issuer,
        validation_policy=validation_policy,
    )
