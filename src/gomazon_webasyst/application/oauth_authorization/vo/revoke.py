from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.api_credential_values import ApiAccessToken


@dataclass(slots=True, frozen=True)
class RevokeTargetProvided:
    token: ApiAccessToken


@dataclass(slots=True, frozen=True)
class RevokeTargetMissing:
    pass


OAuthRevokeTarget: TypeAlias = RevokeTargetProvided | RevokeTargetMissing
