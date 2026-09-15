from typing import Protocol

from gomazon_webasyst.application.api_credential_values import ApiAccessToken, AuthorizationCode


class ApiCredentialGenerator(Protocol):
    def authorization_code(self) -> AuthorizationCode: ...
    def access_token(self) -> ApiAccessToken: ...
