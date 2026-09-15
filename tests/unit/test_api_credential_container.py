from gomazon_webasyst.application.api_credentials import (
    ExchangeAuthorizationCode,
    IssueAuthorizationCode,
    IssueImplicitApiAccessToken,
    ResolveApiAccessToken,
    RevokeApiAccessToken,
)
from gomazon_webasyst.compatibility.webasyst.api_credentials import (
    WebasystApiCredentialGenerator,
    WebasystApiTokenIssuePolicy,
    WebasystAuthorizationCodeExchangePolicy,
    WebasystAuthorizationCodeLifetime,
)
from gomazon_webasyst.composition.api_credentials import create_api_credential_use_cases
from gomazon_webasyst.infrastructure.api_credentials.sqlalchemy.unit_of_work import (
    SQLAlchemyApiCredentialUnitOfWorkFactory,
)


def test_api_credential_composition_wires_five_use_cases_with_shared_dependencies() -> None:
    api = create_api_credential_use_cases(object())

    assert isinstance(api.issue_authorization_code, IssueAuthorizationCode)
    assert isinstance(api.exchange_authorization_code, ExchangeAuthorizationCode)
    assert isinstance(api.issue_implicit_api_access_token, IssueImplicitApiAccessToken)
    assert isinstance(api.resolve_api_access_token, ResolveApiAccessToken)
    assert isinstance(api.revoke_api_access_token, RevokeApiAccessToken)

    uow_factory = api.issue_authorization_code._uow_factory
    assert isinstance(uow_factory, SQLAlchemyApiCredentialUnitOfWorkFactory)
    assert api.exchange_authorization_code._uow_factory is uow_factory
    assert api.issue_implicit_api_access_token._uow_factory is uow_factory
    assert api.resolve_api_access_token._uow_factory is uow_factory
    assert api.revoke_api_access_token._uow_factory is uow_factory

    token_issuer = api.exchange_authorization_code._token_issuer
    assert api.issue_implicit_api_access_token._token_issuer is token_issuer
    assert isinstance(token_issuer._generator, WebasystApiCredentialGenerator)
    assert isinstance(token_issuer._issue_policy, WebasystApiTokenIssuePolicy)
    assert api.issue_authorization_code._generator is token_issuer._generator
    assert isinstance(api.issue_authorization_code._lifetime_policy, WebasystAuthorizationCodeLifetime)
    assert isinstance(
        api.exchange_authorization_code._exchange_policy,
        WebasystAuthorizationCodeExchangePolicy,
    )
