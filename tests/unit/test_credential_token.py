from datetime import datetime
from hashlib import md5

from gomazon_webasyst.compatibility.webasyst.auth.tokens import LegacyCredentialVersionTokenFactory
from gomazon_webasyst.contracts.auth import AuthIdentity


def test_legacy_credential_token_matches_waAuth_getToken_formula():
    identity = AuthIdentity(
        id=42,
        login="admin",
        password_hash="abc123",
        is_user=1,
        create_datetime=datetime(2026, 1, 2, 3, 4, 5),
    )
    digest = md5(b"2026-01-02 03:04:05adminabc123").hexdigest()
    expected = digest[:15] + "42" + digest[-15:]

    assert LegacyCredentialVersionTokenFactory().create(identity) == expected
