from dataclasses import dataclass

from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
)


@dataclass(slots=True, frozen=True)
class OAuthConsentApplication:
    app_id: AppId
    display_name: OAuthAppDisplayName
    icon: OAuthAppIconReference
