from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.api_credentials import (
    ExchangeAuthorizationCode,
    IssueAuthorizationCode,
    IssueImplicitApiAccessToken,
    ResolveApiAccessToken,
    RevokeApiAccessToken,
)
from gomazon_webasyst.application.api_token_issuance import ApiTokenIssuer
from gomazon_webasyst.compatibility.webasyst.api_credentials import (
    WebasystApiCredentialGenerator,
    WebasystApiTokenIssuePolicy,
    WebasystAuthorizationCodeExchangePolicy,
    WebasystAuthorizationCodeLifetime,
)
from gomazon_webasyst.infrastructure.api_credentials.sqlalchemy.unit_of_work import (
    SQLAlchemyApiCredentialUnitOfWorkFactory,
)


@dataclass(slots=True, frozen=True)
class ApiCredentialUseCases:
    issue_authorization_code: IssueAuthorizationCode
    exchange_authorization_code: ExchangeAuthorizationCode
    issue_implicit_api_access_token: IssueImplicitApiAccessToken
    resolve_api_access_token: ResolveApiAccessToken
    revoke_api_access_token: RevokeApiAccessToken


def create_api_credential_use_cases(
    session_factory: async_sessionmaker[AsyncSession],
) -> ApiCredentialUseCases:
    uow_factory = SQLAlchemyApiCredentialUnitOfWorkFactory(session_factory)
    generator = WebasystApiCredentialGenerator()
    token_issuer = ApiTokenIssuer(
        generator=generator,
        issue_policy=WebasystApiTokenIssuePolicy(),
        clock=datetime.now,
    )

    return ApiCredentialUseCases(
        issue_authorization_code=IssueAuthorizationCode(
            uow_factory=uow_factory,
            generator=generator,
            lifetime_policy=WebasystAuthorizationCodeLifetime(),
            clock=datetime.now,
        ),
        exchange_authorization_code=ExchangeAuthorizationCode(
            uow_factory=uow_factory,
            token_issuer=token_issuer,
            exchange_policy=WebasystAuthorizationCodeExchangePolicy(),
            clock=datetime.now,
        ),
        issue_implicit_api_access_token=IssueImplicitApiAccessToken(
            uow_factory=uow_factory,
            token_issuer=token_issuer,
        ),
        resolve_api_access_token=ResolveApiAccessToken(
            uow_factory=uow_factory,
            clock=datetime.now,
        ),
        revoke_api_access_token=RevokeApiAccessToken(
            uow_factory=uow_factory,
        ),
    )
