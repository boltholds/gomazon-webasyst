from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.auth import (
    AuthenticateBackendPassword,
    LogoutBackendSession,
    ResolveBackendSession,
)
from gomazon_webasyst.application.ports.session_validation import (
    SessionValidationPolicy,
    StrictSessionValidationPolicy,
)
from gomazon_webasyst.compatibility.webasyst.auth.factory import create_webasyst_login_policy_set
from gomazon_webasyst.compatibility.webasyst.auth.passwords import LegacyMd5PasswordVerifier
from gomazon_webasyst.compatibility.webasyst.auth.phone import LegacyPhonePrefixPolicy
from gomazon_webasyst.compatibility.webasyst.auth.tokens import LegacyCredentialVersionTokenFactory
from gomazon_webasyst.infrastructure.auth.identity_directory import create_sqlalchemy_identity_directory
from gomazon_webasyst.infrastructure.auth.session_registry import SQLAlchemyAuthSessionRegistry
from gomazon_webasyst.infrastructure.auth.subjects import SQLAlchemyAuthSubjectStore
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore


@dataclass(slots=True, frozen=True)
class AuthUseCases:
    authenticate_backend_password: AuthenticateBackendPassword
    resolve_backend_session: ResolveBackendSession
    logout_backend_session: LogoutBackendSession


def create_auth_use_cases(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    phone_prefix_policy: LegacyPhonePrefixPolicy = LegacyPhonePrefixPolicy(),
    validation_policy: SessionValidationPolicy = StrictSessionValidationPolicy(),
) -> AuthUseCases:
    planner = create_webasyst_login_policy_set()
    directory = create_sqlalchemy_identity_directory(
        session_factory,
        phone_candidates=phone_prefix_policy.candidates,
    )
    subjects = SQLAlchemyAuthSubjectStore(session_factory)
    verifier = LegacyMd5PasswordVerifier()
    token_factory = LegacyCredentialVersionTokenFactory()
    session_state = InMemorySessionStateStore()
    registry = SQLAlchemyAuthSessionRegistry(session_factory)

    return AuthUseCases(
        authenticate_backend_password=AuthenticateBackendPassword(
            planner=planner,
            identity_directory=directory,
            password_verifier=verifier,
            token_factory=token_factory,
            session_state=session_state,
            session_registry=registry,
        ),
        resolve_backend_session=ResolveBackendSession(
            session_state=session_state,
            subject_store=subjects,
            token_factory=token_factory,
            session_registry=registry,
            validation_policy=validation_policy,
        ),
        logout_backend_session=LogoutBackendSession(
            session_state=session_state,
            session_registry=registry,
        ),
    )
