from types import SimpleNamespace

from gomazon_webasyst.composition.container import Container
from gomazon_webasyst.composition.settings import Settings


async def noop_close():
    return None


def test_container_exposes_auth_session_use_cases_as_first_class_dependencies():
    engine = SimpleNamespace(dispose=noop_close)
    authenticate = object()
    resolve = object()
    logout = object()
    issue_persistent = object()
    restore_persistent = object()
    revoke_persistent = object()
    container = Container(
        settings=Settings(database_url="sqlite+aiosqlite:///:memory:"),
        engine=engine,
        get_contact=object(),
        create_contact=object(),
        update_contact=object(),
        authenticate_backend_password=authenticate,
        resolve_backend_session=resolve,
        logout_backend_session=logout,
        issue_persistent_credential=issue_persistent,
        restore_backend_session_from_persistent_credential=restore_persistent,
        revoke_persistent_credential=revoke_persistent,
    )

    assert container.authenticate_backend_password is authenticate
    assert container.resolve_backend_session is resolve
    assert container.logout_backend_session is logout
    assert container.issue_persistent_credential is issue_persistent
    assert container.restore_backend_session_from_persistent_credential is restore_persistent
    assert container.revoke_persistent_credential is revoke_persistent


def test_auth_composition_accepts_explicit_session_validation_policy():
    from gomazon_webasyst.application.ports.session_validation import SessionValidationDecision
    from gomazon_webasyst.composition.auth import create_auth_use_cases

    class TrustStoredPolicy:
        def decide(self, state):
            return SessionValidationDecision.TRUST_STORED

    policy = TrustStoredPolicy()
    auth = create_auth_use_cases(object(), validation_policy=policy)

    assert auth.resolve_backend_session._validation_policy is policy
