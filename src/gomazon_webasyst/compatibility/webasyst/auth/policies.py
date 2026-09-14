import re
from collections.abc import Callable, Iterable

from gomazon_webasyst.application.ports.login_policy import LoginPolicy
from gomazon_webasyst.contracts.auth import (
    IdentityKey,
    IdentityLookupPlan,
    LoginPlanBuilt,
    LoginPlanError,
    LoginPlanResult,
    LoginPolicyContext,
    PolicyContribute,
    PolicyReject,
    PolicySkip,
)
from gomazon_webasyst.contracts.enums import LoginPlanErrorType, LoginPolicyRejectType


_EMAIL_RE = re.compile(r"^[^\s@]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z0-9-]+$")
_PHONE_RE = re.compile(r"^[0-9\-() /+\s]*$")


def is_webasyst_email(value: str) -> bool:
    return bool(value) and "<script" not in value.lower() and bool(_EMAIL_RE.fullmatch(value))


def is_webasyst_phone(value: str) -> bool:
    return bool(value) and bool(_PHONE_RE.fullmatch(value))


class PreferredSchemePolicy:
    def __init__(self, scheme: str, predicate: Callable[[str], bool]) -> None:
        self._scheme = scheme
        self._predicate = predicate

    def evaluate(self, value: str, context: LoginPolicyContext):
        if self._scheme not in context.enabled_schemes or not self._predicate(value):
            return PolicySkip()
        return PolicyContribute(keys=(IdentityKey(scheme=self._scheme, value=value),))


class ConfiguredSchemesPolicy:
    def evaluate(self, value: str, context: LoginPolicyContext):
        if not context.enabled_schemes:
            return PolicyReject(type=LoginPolicyRejectType.INVALID_IDENTIFIER)
        return PolicyContribute(
            keys=tuple(IdentityKey(scheme=scheme, value=value) for scheme in context.enabled_schemes)
        )


class LoginPolicySet:
    def __init__(self, policies: Iterable[LoginPolicy]) -> None:
        self._policies = tuple(policies)

    def plan(self, value: str, context: LoginPolicyContext) -> LoginPlanResult:
        if not value:
            return LoginPlanError(type=LoginPlanErrorType.EMPTY_IDENTIFIER)

        keys: list[IdentityKey] = []
        seen: set[tuple[str, str]] = set()
        for policy in self._policies:
            decision = policy.evaluate(value, context)
            if isinstance(decision, PolicyReject):
                return LoginPlanError(type=LoginPlanErrorType.REJECTED_BY_POLICY)
            if isinstance(decision, PolicySkip):
                continue
            for key in decision.keys:
                marker = (key.scheme, key.value)
                if marker not in seen:
                    seen.add(marker)
                    keys.append(key)

        if not keys:
            return LoginPlanError(type=LoginPlanErrorType.REJECTED_BY_POLICY)
        return LoginPlanBuilt(plan=IdentityLookupPlan(keys=tuple(keys)))
