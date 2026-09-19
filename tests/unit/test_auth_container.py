from types import SimpleNamespace

from gomazon_webasyst.composition.container import Container
from gomazon_webasyst.composition.settings import Settings


async def noop_close():
    return None


def _access_control_fields() -> dict[str, object]:
    return {
        "get_group": object(),
        "list_groups": object(),
        "list_user_groups": object(),
        "list_group_members": object(),
        "get_effective_right": object(),
        "get_app_access": object(),
        "get_rights_snapshot": object(),
        "create_group": object(),
        "update_group": object(),
        "delete_group": object(),
        "add_group_member": object(),
        "remove_group_member": object(),
        "replace_group_members": object(),
        "assign_right": object(),
        "revoke_right": object(),
        "set_app_access": object(),
        "set_global_admin_access": object(),
    }


def _api_credential_fields() -> dict[str, object]:
    return {
        "issue_authorization_code": object(),
        "exchange_authorization_code": object(),
        "issue_implicit_api_access_token": object(),
        "resolve_api_access_token": object(),
        "revoke_api_access_token": object(),
    }


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
        backend_session_bridge=object(),
        api_execution=object(),
        oauth_authorization=object(),
        **_api_credential_fields(),
        **_access_control_fields(),
    )

    assert container.authenticate_backend_password is authenticate
    assert container.resolve_backend_session is resolve
    assert container.logout_backend_session is logout
    assert container.issue_persistent_credential is issue_persistent
    assert container.restore_backend_session_from_persistent_credential is restore_persistent
    assert container.revoke_persistent_credential is revoke_persistent


def test_auth_composition_reuses_supplied_session_state_store():
    from gomazon_webasyst.composition.auth import create_auth_use_cases

    session_state = object()
    auth = create_auth_use_cases(object(), session_state=session_state)

    assert auth.resolve_backend_session._session_state is session_state
    assert auth.logout_backend_session._session_state is session_state
    assert auth.authenticate_backend_password._session_establisher._session_state is session_state
    assert (
        auth.restore_backend_session_from_persistent_credential._session_establisher._session_state
        is session_state
    )


def test_auth_composition_accepts_explicit_session_validation_policy():
    from gomazon_webasyst.application.ports.session_validation import SessionValidationDecision
    from gomazon_webasyst.composition.auth import create_auth_use_cases

    class TrustStoredPolicy:
        def decide(self, state):
            return SessionValidationDecision.TRUST_STORED

    policy = TrustStoredPolicy()
    auth = create_auth_use_cases(
        object(),
        session_state=object(),
        validation_policy=policy,
    )

    assert auth.resolve_backend_session._validation_policy is policy
