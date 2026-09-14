from gomazon_webasyst.compatibility.webasyst.auth.policies import (
    ConfiguredSchemesPolicy,
    LoginPolicySet,
    PreferredSchemePolicy,
    is_webasyst_email,
    is_webasyst_phone,
)
from gomazon_webasyst.contracts.auth import LoginPlanBuilt, LoginPolicyContext


def test_waAuth_getByLogin_prioritizes_email_shape_then_falls_back_to_configured_fields():
    policies = LoginPolicySet(
        policies=(
            PreferredSchemePolicy("email", is_webasyst_email),
            PreferredSchemePolicy("phone", is_webasyst_phone),
            ConfiguredSchemesPolicy(),
        )
    )

    result = policies.plan(
        "user@example.com",
        LoginPolicyContext(enabled_schemes=("login", "email", "phone")),
    )

    assert isinstance(result, LoginPlanBuilt)
    assert [key.scheme for key in result.plan.keys] == ["email", "login", "phone"]


def test_waPhoneNumberValidator_accepts_legacy_punctuation_and_rejects_letters():
    assert is_webasyst_phone("+7 (999) 123-45-67")
    assert is_webasyst_phone("8/999/123 45 67")
    assert not is_webasyst_phone("phone123")
    assert not is_webasyst_phone("")
