import re
from collections.abc import Callable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.ports.identity_directory import IdentityKeyResolver
from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    IdentityKey,
    IdentityKeyNotFound,
    IdentityKeyResolved,
    IdentityLookupPlan,
    IdentityResolved,
    IdentityResolution,
    IdentityResolutionError,
)
from gomazon_webasyst.contracts.enums import IdentityResolutionErrorType
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRow,
)


def _identity(row: WaContactRow) -> AuthIdentity:
    return AuthIdentity(
        id=row.id,
        login=row.login or "",
        password_hash=row.password,
        is_user=row.is_user,
        create_datetime=row.create_datetime,
    )


def clean_legacy_phone(value: str) -> str:
    value = value.strip()
    for char in "+-()":
        value = value.replace(char, "")
    return re.sub(r"(\d)\s+(\d)", r"\1\2", value)


class ResolverRegistryIdentityDirectory:
    def __init__(self, resolvers: Mapping[str, IdentityKeyResolver]) -> None:
        self._resolvers = dict(resolvers)

    def register(self, scheme: str, resolver: IdentityKeyResolver) -> None:
        if not scheme:
            raise ValueError("identity scheme must not be empty")
        self._resolvers[scheme] = resolver

    async def resolve(self, plan: IdentityLookupPlan) -> IdentityResolution:
        for key in plan.keys:
            resolver = self._resolvers.get(key.scheme)
            if resolver is None:
                return IdentityResolutionError(type=IdentityResolutionErrorType.UNSUPPORTED_SCHEME)
            result = await resolver.resolve(key)
            if isinstance(result, IdentityKeyResolved):
                return IdentityResolved(identity=result.identity, matched_key=key)
        return IdentityResolutionError(type=IdentityResolutionErrorType.NOT_FOUND)


class _SQLAlchemyIdentityResolver:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        scheme: str,
        value_candidates: Callable[[str], tuple[str, ...]] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._scheme = scheme
        self._value_candidates = value_candidates or (lambda value: (value,))

    async def resolve(self, key: IdentityKey):
        if key.scheme != self._scheme:
            return IdentityKeyNotFound()
        async with self._session_factory() as session:
            for value in self._value_candidates(key.value):
                row = await self._load(session, value)
                if row is not None:
                    return IdentityKeyResolved(identity=_identity(row))
        return IdentityKeyNotFound()

    async def _load(self, session: AsyncSession, value: str) -> WaContactRow | None:
        base = [WaContactRow.is_user == 1, WaContactRow.password != ""]
        if self._scheme == "login":
            statement = (
                select(WaContactRow)
                .where(*base, WaContactRow.login == value)
                .order_by(WaContactRow.id)
                .limit(1)
            )
        elif self._scheme == "email":
            statement = (
                select(WaContactRow)
                .join(WaContactEmailRow, WaContactEmailRow.contact_id == WaContactRow.id)
                .where(*base, WaContactEmailRow.email == value, WaContactEmailRow.sort == 0)
                .order_by(WaContactRow.id)
                .limit(1)
            )
        elif self._scheme == "phone":
            statement = (
                select(WaContactRow)
                .join(WaContactDataRow, WaContactDataRow.contact_id == WaContactRow.id)
                .where(
                    *base,
                    WaContactDataRow.field == "phone",
                    WaContactDataRow.value == clean_legacy_phone(value),
                    WaContactDataRow.sort == 0,
                )
                .order_by(WaContactRow.id)
                .limit(1)
            )
        else:
            return None
        return (await session.execute(statement)).scalars().first()


def create_sqlalchemy_identity_directory(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    phone_candidates: Callable[[str], tuple[str, ...]] | None = None,
) -> ResolverRegistryIdentityDirectory:
    phone_candidates = phone_candidates or (lambda value: (clean_legacy_phone(value),))
    return ResolverRegistryIdentityDirectory(
        {
            "login": _SQLAlchemyIdentityResolver(session_factory, "login"),
            "email": _SQLAlchemyIdentityResolver(session_factory, "email"),
            "phone": _SQLAlchemyIdentityResolver(
                session_factory,
                "phone",
                value_candidates=phone_candidates,
            ),
        }
    )
