from types import TracebackType
from typing import Callable, Protocol

from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenRepository,
    AuthorizationCodeRepository,
)


class ApiCredentialUnitOfWork(Protocol):
    @property
    def authorization_codes(self) -> AuthorizationCodeRepository: ...

    @property
    def tokens(self) -> ApiTokenRepository: ...

    async def __aenter__(self) -> "ApiCredentialUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


ApiCredentialUnitOfWorkFactory = Callable[[], ApiCredentialUnitOfWork]
