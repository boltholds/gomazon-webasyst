import pytest

from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    IdentityKey,
    IdentityKeyNotFound,
    IdentityKeyResolved,
    IdentityLookupPlan,
    IdentityResolved,
    IdentityResolutionError,
)
from gomazon_webasyst.contracts.enums import IdentityResolutionErrorType
from gomazon_webasyst.infrastructure.auth.identity_directory import ResolverRegistryIdentityDirectory


class FakeResolver:
    def __init__(self, result):
        self.result = result
        self.seen: list[IdentityKey] = []

    async def resolve(self, key: IdentityKey):
        self.seen.append(key)
        return self.result


def identity(contact_id: int, login: str = "user") -> AuthIdentity:
    from datetime import datetime

    return AuthIdentity(
        id=contact_id,
        login=login,
        password_hash="hash",
        is_user=1,
        create_datetime=datetime(2026, 1, 1),
    )


@pytest.mark.asyncio
async def test_directory_returns_first_success_in_plan_order():
    login = FakeResolver(IdentityKeyNotFound())
    email_identity = identity(2, "alice")
    email = FakeResolver(IdentityKeyResolved(identity=email_identity))
    phone = FakeResolver(IdentityKeyResolved(identity=identity(3, "other")))
    directory = ResolverRegistryIdentityDirectory(
        {"login": login, "email": email, "phone": phone}
    )
    plan = IdentityLookupPlan(
        keys=(
            IdentityKey(scheme="login", value="alice@example.com"),
            IdentityKey(scheme="email", value="alice@example.com"),
            IdentityKey(scheme="phone", value="alice@example.com"),
        )
    )

    result = await directory.resolve(plan)

    assert isinstance(result, IdentityResolved)
    assert result.identity == email_identity
    assert result.matched_key.scheme == "email"
    assert len(phone.seen) == 0


@pytest.mark.asyncio
async def test_directory_returns_explicit_not_found_after_all_resolvers_miss():
    directory = ResolverRegistryIdentityDirectory(
        {
            "login": FakeResolver(IdentityKeyNotFound()),
            "email": FakeResolver(IdentityKeyNotFound()),
        }
    )
    result = await directory.resolve(
        IdentityLookupPlan(
            keys=(
                IdentityKey(scheme="login", value="missing"),
                IdentityKey(scheme="email", value="missing"),
            )
        )
    )

    assert isinstance(result, IdentityResolutionError)
    assert result.type is IdentityResolutionErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_directory_returns_explicit_unsupported_scheme():
    directory = ResolverRegistryIdentityDirectory({})

    result = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="employee_id", value="EMP-42"),))
    )

    assert isinstance(result, IdentityResolutionError)
    assert result.type is IdentityResolutionErrorType.UNSUPPORTED_SCHEME


@pytest.mark.asyncio
async def test_directory_can_register_new_scheme_without_api_change():
    employee_identity = identity(42, "employee")
    directory = ResolverRegistryIdentityDirectory({})
    directory.register(
        "employee_id",
        FakeResolver(IdentityKeyResolved(identity=employee_identity)),
    )

    result = await directory.resolve(
        IdentityLookupPlan(keys=(IdentityKey(scheme="employee_id", value="EMP-42"),))
    )

    assert isinstance(result, IdentityResolved)
    assert result.identity.id == 42


def test_phone_prefix_transform_matches_webasyst_direct_and_reverse_rules():
    from gomazon_webasyst.compatibility.webasyst.auth.phone import LegacyPhonePrefixPolicy

    policy = LegacyPhonePrefixPolicy(input_code="8", output_code="7")

    assert policy.candidates("812345") == ("812345", "712345")
    assert policy.candidates("+712345") == ("712345", "812345")
    assert policy.candidates("612345") == ("612345",)
