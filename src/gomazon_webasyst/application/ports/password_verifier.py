from typing import Protocol

from pydantic import SecretStr

from gomazon_webasyst.contracts.auth import PasswordVerification


class PasswordVerifier(Protocol):
    def verify(self, candidate: SecretStr, stored_hash: str) -> PasswordVerification: ...
