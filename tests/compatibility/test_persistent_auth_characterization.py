from datetime import datetime, timedelta
from hashlib import md5

from gomazon_webasyst.compatibility.webasyst.auth.persistent import (
    LEGACY_AUTH_TOKEN_LIFETIME,
    LegacyAuthTokenParser,
)
from gomazon_webasyst.compatibility.webasyst.auth.tokens import LegacyCredentialVersionTokenFactory
from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.contracts.auth import AuthIdentity, BackendPasswordCredentials


def test_waAuth_getToken_matches_4_2_0_formula_exactly():
    identity = AuthIdentity(
        id=123,
        login="admin",
        password_hash="legacy-hash",
        is_user=1,
        create_datetime=datetime(2026, 1, 2, 3, 4, 5),
    )
    source_string = "2026-01-02 03:04:05adminlegacy-hash"
    digest = md5(source_string.encode()).hexdigest()
    expected = f"{digest[:15]}123{digest[-15:]}"

    assert LegacyCredentialVersionTokenFactory().create(identity) == expected


def test_waAuth_authByCookie_contact_id_is_middle_between_15_char_parts():
    identity = AuthIdentity(
        id=987654,
        login="admin",
        password_hash="legacy-hash",
        is_user=1,
        create_datetime=datetime(2026, 1, 2, 3, 4, 5),
    )
    token = LegacyCredentialVersionTokenFactory().create(identity)

    parsed = LegacyAuthTokenParser().parse(PersistentCredential(token))

    assert parsed.credential.contact_id == 987654


def test_waAuth_remember_and_authByCookie_use_30_day_auth_token_lifetime():
    assert LEGACY_AUTH_TOKEN_LIFETIME.value == timedelta(seconds=2592000)


def test_waAuth_remember_ui_preference_does_not_leak_into_password_credentials():
    assert "remember" not in BackendPasswordCredentials.model_fields
