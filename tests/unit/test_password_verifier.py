from hashlib import md5

from pydantic import SecretStr

from gomazon_webasyst.compatibility.webasyst.auth.passwords import LegacyMd5PasswordVerifier
from gomazon_webasyst.contracts.auth import PasswordAccepted, PasswordVerificationError
from gomazon_webasyst.contracts.enums import PasswordVerificationErrorType


def test_legacy_md5_verifier_accepts_matching_password():
    verifier = LegacyMd5PasswordVerifier()
    stored = md5(b"secret").hexdigest()

    result = verifier.verify(SecretStr("secret"), stored)

    assert isinstance(result, PasswordAccepted)


def test_legacy_md5_verifier_returns_explicit_invalid_result():
    verifier = LegacyMd5PasswordVerifier()
    stored = md5(b"secret").hexdigest()

    result = verifier.verify(SecretStr("wrong"), stored)

    assert isinstance(result, PasswordVerificationError)
    assert result.type is PasswordVerificationErrorType.INVALID
