from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId, RightName


@dataclass(slots=True, frozen=True)
class GlobalControlApp:
    app_id: AppId


@dataclass(slots=True, frozen=True)
class RegularApp:
    app_id: AppId


AppClassification: TypeAlias = GlobalControlApp | RegularApp


@dataclass(slots=True, frozen=True)
class RightFallbackAvailable:
    name: RightName


@dataclass(slots=True, frozen=True)
class RightFallbackUnavailable:
    pass


RightFallbackDecision: TypeAlias = RightFallbackAvailable | RightFallbackUnavailable


class AccessSemantics(Protocol):
    def global_control_app(self) -> GlobalControlApp: ...

    def classify_app(self, app_id: AppId) -> AppClassification: ...


class RightFallbackPolicy(Protocol):
    def fallback(self, name: RightName) -> RightFallbackDecision: ...
