from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class AppLicenseGranted:
    app_id: AppId


@dataclass(slots=True, frozen=True)
class AppLicenseBlocked:
    app_id: AppId


AppLicenseDecision: TypeAlias = AppLicenseGranted | AppLicenseBlocked


class AppLicensePolicy(Protocol):
    async def check(self, app_id: AppId) -> AppLicenseDecision: ...
