from gomazon_webasyst.application.persistent_login import (
    IssuePersistentCredential,
    RestoreBackendSessionFromPersistentCredential,
    RevokePersistentCredential,
)
from gomazon_webasyst.compatibility.webasyst.auth.persistent import (
    LegacyAuthTokenIssuer,
    LegacyAuthTokenStrategy,
)
from gomazon_webasyst.composition.auth import (
    create_auth_use_cases,
    create_auth_use_cases_with_persistent_credentials,
)
from gomazon_webasyst.infrastructure.auth.persistent_credentials import (
    OrderedPersistentCredentialResolver,
)


class CustomResolver:
    async def resolve(self, credential):
        raise AssertionError("not called in composition test")


class CustomIssuer:
    async def issue(self, identity):
        raise AssertionError("not called in composition test")


def test_default_auth_composition_exposes_persistent_login_use_cases():
    auth = create_auth_use_cases(object(), session_state=object())

    assert isinstance(auth.issue_persistent_credential, IssuePersistentCredential)
    assert isinstance(
        auth.restore_backend_session_from_persistent_credential,
        RestoreBackendSessionFromPersistentCredential,
    )
    assert isinstance(auth.revoke_persistent_credential, RevokePersistentCredential)

    resolver = auth.restore_backend_session_from_persistent_credential._resolver
    issuer = auth.issue_persistent_credential._issuer
    assert isinstance(resolver, OrderedPersistentCredentialResolver)
    assert len(resolver._strategies) == 1
    assert isinstance(resolver._strategies[0], LegacyAuthTokenStrategy)
    assert isinstance(issuer, LegacyAuthTokenIssuer)


def test_password_and_persistent_restore_share_one_session_establisher():
    auth = create_auth_use_cases(object(), session_state=object())

    assert (
        auth.authenticate_backend_password._session_establisher
        is auth.restore_backend_session_from_persistent_credential._session_establisher
    )


def test_custom_persistent_resolver_and_issuer_are_injected_explicitly():
    resolver = CustomResolver()
    issuer = CustomIssuer()
    session_state = object()

    auth = create_auth_use_cases_with_persistent_credentials(
        object(),
        session_state=session_state,
        persistent_resolver=resolver,
        persistent_issuer=issuer,
    )

    assert auth.restore_backend_session_from_persistent_credential._resolver is resolver
    assert auth.issue_persistent_credential._issuer is issuer
    assert auth.resolve_backend_session._session_state is session_state
    assert auth.logout_backend_session._session_state is session_state
