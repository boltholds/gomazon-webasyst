from gomazon_webasyst.compatibility.webasyst.auth.policies import (
    ConfiguredSchemesPolicy,
    LoginPolicySet,
    PreferredSchemePolicy,
    is_webasyst_email,
    is_webasyst_phone,
)


def create_webasyst_login_policy_set() -> LoginPolicySet:
    return LoginPolicySet(
        policies=(
            PreferredSchemePolicy("email", is_webasyst_email),
            PreferredSchemePolicy("phone", is_webasyst_phone),
            ConfiguredSchemesPolicy(),
        )
    )
