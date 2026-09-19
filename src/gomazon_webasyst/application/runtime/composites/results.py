from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.vo.identity import PluginKey
from gomazon_webasyst.contracts.enums import RuntimeLinkRejectReason


@dataclass(slots=True, frozen=True)
class RuntimeLinkIssue:
    reason: RuntimeLinkRejectReason
    subject: str

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("runtime link issue subject must not be empty")


@dataclass(slots=True, frozen=True)
class RuntimeLinkSucceeded:
    applications: tuple[AppId, ...]
    plugins: tuple[PluginKey, ...]


@dataclass(slots=True, frozen=True)
class RuntimeLinkRejected:
    issues: tuple[RuntimeLinkIssue, ...]

    def __post_init__(self) -> None:
        if not self.issues:
            raise ValueError("runtime link rejection requires at least one issue")


RuntimeLinkResult: TypeAlias = RuntimeLinkSucceeded | RuntimeLinkRejected
