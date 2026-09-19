from datetime import datetime, timezone
from importlib import import_module
from types import SimpleNamespace

import pytest

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.enums import PersistentLoginMode


NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


def _composition():
    try:
        return import_module("gomazon_webasyst.composition.backend_session_bridge")
    except ModuleNotFoundError as error:
        pytest.fail(f"backend session bridge composition missing: {error}")


def fake_auth_use_cases():
    return SimpleNamespace(
        authenticate_backend_password=object(),
        resolve_backend_session=object(),
        logout_backend_session=object(),
        issue_persistent_credential=object(),
        restore_backend_session_from_persistent_credential=object(),
        revoke_persistent_credential=object(),
    )


def test_bridge_composition_reuses_existing_auth_use_cases() -> None:
    module = _composition()
    auth = fake_auth_use_cases()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    bridge = module.create_backend_session_bridge_components(
        auth,
        settings,
        clock=lambda: NOW,
    )

    assert bridge.current_subject_flow._resolve_backend_session is auth.resolve_backend_session
    assert (
        bridge.current_subject_flow._restore_backend_session_from_persistent_credential
        is auth.restore_backend_session_from_persistent_credential
    )
    assert (
        bridge.password_login_flow._authenticate_backend_password
        is auth.authenticate_backend_password
    )
    assert bridge.password_login_flow._issue_persistent_credential is auth.issue_persistent_credential
    assert bridge.logout_flow._logout_backend_session is auth.logout_backend_session
    assert bridge.logout_flow._revoke_persistent_credential is auth.revoke_persistent_credential
    assert bridge.persistent_login_mode is PersistentLoginMode.ENABLED


def test_disabled_setting_becomes_typed_mode() -> None:
    module = _composition()
    bridge = module.create_backend_session_bridge_components(
        fake_auth_use_cases(),
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            persistent_login_enabled=False,
        ),
        clock=lambda: NOW,
    )
    assert bridge.persistent_login_mode is PersistentLoginMode.DISABLED


def test_cookie_names_are_validated_at_composition_startup() -> None:
    module = _composition()
    with pytest.raises(ValueError, match="cookie name"):
        module.create_backend_session_bridge_components(
            fake_auth_use_cases(),
            Settings(
                database_url="sqlite+aiosqlite:///:memory:",
                backend_session_cookie_name="bad cookie",
            ),
            clock=lambda: NOW,
        )


def test_settings_expose_bridge_cookie_defaults() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert settings.backend_session_cookie_name == "gomazon_session"
    assert settings.persistent_auth_cookie_name == "auth_token"
    assert settings.backend_auth_cookie_secure is False
    assert settings.persistent_login_enabled is True
