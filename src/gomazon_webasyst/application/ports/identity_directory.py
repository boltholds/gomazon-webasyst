from typing import Protocol

from gomazon_webasyst.contracts.auth import (
    IdentityKey,
    IdentityKeyResolution,
    IdentityLookupPlan,
    IdentityResolution,
)


class IdentityKeyResolver(Protocol):
    async def resolve(self, key: IdentityKey) -> IdentityKeyResolution: ...


class IdentityDirectory(Protocol):
    async def resolve(self, plan: IdentityLookupPlan) -> IdentityResolution: ...
