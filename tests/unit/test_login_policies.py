from pydantic import TypeAdapter

from gomazon_webasyst.compatibility.webasyst.auth.policies import (
    ConfiguredSchemesPolicy,
    LoginPolicySet,
    PreferredSchemePolicy,
    is_webasyst_email,
    is_webasyst_phone,
)
from gomazon_webasyst.contracts.auth import (
    IdentityKey,
    LoginPlanBuilt,
    LoginPlanError,
    LoginPlanResult,
    LoginPolicyContext,
)
from gomazon_webasyst.contracts.enums import LoginPlanErrorType


def make_policy_set(*extra):
    return LoginPolicySet(
        policies=(
            PreferredSchemePolicy("email", is_webasyst_email),
            PreferredSchemePolicy("phone", is_webasyst_phone),
            *extra,
            ConfiguredSchemesPolicy(),
        )
    )


def test_valid_email_is_prioritized_then_configured_order_continues():
    result = make_policy_set().plan(
        "alice@example.com",
        LoginPolicyContext(enabled_schemes=("login", "email", "phone")),
    )

    assert isinstance(result, LoginPlanBuilt)
    assert result.plan.keys == (
        IdentityKey(scheme="email", value="alice@example.com"),
        IdentityKey(scheme="login", value="alice@example.com"),
        IdentityKey(scheme="phone", value="alice@example.com"),
    )


def test_disabled_preferred_scheme_is_not_added():
    result = make_policy_set().plan(
        "alice@example.com",
        LoginPolicyContext(enabled_schemes=("login", "phone")),
    )

    assert isinstance(result, LoginPlanBuilt)
    assert tuple(key.scheme for key in result.plan.keys) == ("login", "phone")


def test_valid_phone_is_prioritized_before_configured_fallback():
    result = make_policy_set().plan(
        "+31 (20) 123-4567",
        LoginPolicyContext(enabled_schemes=("login", "email", "phone")),
    )

    assert isinstance(result, LoginPlanBuilt)
    assert tuple(key.scheme for key in result.plan.keys) == ("phone", "login", "email")


def test_plain_login_uses_configured_scheme_order():
    result = make_policy_set().plan(
        "admin",
        LoginPolicyContext(enabled_schemes=("login", "email", "phone")),
    )

    assert isinstance(result, LoginPlanBuilt)
    assert tuple(key.scheme for key in result.plan.keys) == ("login", "email", "phone")


def test_blank_identifier_returns_explicit_plan_error():
    result = make_policy_set().plan(
        "",
        LoginPolicyContext(enabled_schemes=("login", "email")),
    )

    assert isinstance(result, LoginPlanError)
    assert result.type is LoginPlanErrorType.EMPTY_IDENTIFIER
    assert TypeAdapter(LoginPlanResult).dump_python(result, mode="json") == {
        "kind": "error",
        "type": "empty_identifier",
    }


def test_new_scheme_is_added_by_registering_policy_without_core_branch():
    employee_policy = PreferredSchemePolicy(
        "employee_id",
        lambda value: value.startswith("EMP-"),
    )
    result = make_policy_set(employee_policy).plan(
        "EMP-42",
        LoginPolicyContext(enabled_schemes=("login", "employee_id")),
    )

    assert isinstance(result, LoginPlanBuilt)
    assert tuple(key.scheme for key in result.plan.keys) == ("employee_id", "login")
