from typing import Protocol

from gomazon_webasyst.contracts.auth import AuthIdentity


class CredentialVersionTokenFactory(Protocol):
    def create(self, identity: AuthIdentity) -> str: ...
