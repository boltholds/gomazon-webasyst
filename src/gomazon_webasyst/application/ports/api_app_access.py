from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class ApiAppAccessGranted:
    contact_id: int
    app_id: AppId


@dataclass(slots=True, frozen=True)
class ApiAppAccessDenied:
    contact_id: int
    app_id: AppId


@dataclass(slots=True, frozen=True)
class ApiAppSubjectUnavailable:
    contact_id: int
    app_id: AppId


ApiAppAccessDecision: TypeAlias = (
    ApiAppAccessGranted | ApiAppAccessDenied | ApiAppSubjectUnavailable
)


class ApiAppAccessPolicy(Protocol):
    async def authorize(self, contact_id: int, app_id: AppId) -> ApiAppAccessDecision: ...
