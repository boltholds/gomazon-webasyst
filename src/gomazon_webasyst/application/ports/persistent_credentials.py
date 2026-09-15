from typing import Protocol

from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.contracts.auth import AuthIdentity
from gomazon_webasyst.contracts.persistent_login import (
    PersistentCredentialIssueResult,
    PersistentCredentialResolution,
    PersistentCredentialStrategyResult,
)


class PersistentCredentialStrategy(Protocol):
    async def resolve(
        self,
        credential: PersistentCredential,
    ) -> PersistentCredentialStrategyResult: ...


class PersistentCredentialResolver(Protocol):
    async def resolve(
        self,
        credential: PersistentCredential,
    ) -> PersistentCredentialResolution: ...


class PersistentCredentialIssuer(Protocol):
    async def issue(
        self,
        identity: AuthIdentity,
    ) -> PersistentCredentialIssueResult: ...
