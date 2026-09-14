from hashlib import md5
from hmac import compare_digest

from pydantic import SecretStr

from gomazon_webasyst.contracts.auth import PasswordAccepted, PasswordVerification, PasswordVerificationError
from gomazon_webasyst.contracts.enums import PasswordVerificationErrorType


class LegacyMd5PasswordVerifier:
    def verify(self, candidate: SecretStr, stored_hash: str) -> PasswordVerification:
        digest = md5(candidate.get_secret_value().encode()).hexdigest()
        if stored_hash and compare_digest(digest, stored_hash):
            return PasswordAccepted()
        return PasswordVerificationError(type=PasswordVerificationErrorType.INVALID)
