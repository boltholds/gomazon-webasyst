from typing import Protocol

from gomazon_webasyst.application.auth_values import AuthSessionKey
from gomazon_webasyst.contracts.auth import (
    AuthSessionRegistration,
    RegistryCheckResult,
    RegistryRevocationResult,
    RegistryTouchResult,
    RegistryWritten,
)


class AuthSessionRegistry(Protocol):
    async def register(self, registration: AuthSessionRegistration) -> RegistryWritten: ...
    async def check(self, key: AuthSessionKey) -> RegistryCheckResult: ...
    async def touch(self, key: AuthSessionKey) -> RegistryTouchResult: ...
    async def revoke(self, key: AuthSessionKey) -> RegistryRevocationResult: ...
