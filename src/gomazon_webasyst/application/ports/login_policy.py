from typing import Protocol

from gomazon_webasyst.contracts.auth import LoginPlanResult, LoginPolicyContext, LoginPolicyDecision


class LoginPolicy(Protocol):
    def evaluate(self, value: str, context: LoginPolicyContext) -> LoginPolicyDecision: ...


class LoginPlanner(Protocol):
    def plan(self, value: str, context: LoginPolicyContext) -> LoginPlanResult: ...
