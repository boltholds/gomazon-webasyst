from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import (
    LegacyApiCredentialExtractionService,
)
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import (
    AuthorizationHeader,
    NoAuthorizationHeader,
)


def _extractor():
    from gomazon_webasyst.compatibility.webasyst.oauth.services.revoke_target import (
        LegacyRevokeTargetExtractor,
    )
    return LegacyRevokeTargetExtractor()


def test_form_token_shadows_query_and_becomes_revoke_target() -> None:
    credential = LegacyApiCredentialExtractionService().extract(
        query=ApiParameterMap({"access_token": "query-a"}),
        form=ApiParameterMap({"access_token": "form-a"}),
        authorization=AuthorizationHeader("Bearer header-b"),
        server_authorization=NoAuthorizationHeader(),
    )
    target = _extractor().extract(
        query=ApiParameterMap({"access_token": "query-a"}),
        form=ApiParameterMap({"access_token": "form-a"}),
    )
    assert credential.token.value == "form-a"
    assert target.token.value == "form-a"


def test_empty_form_token_shadows_query_for_target_but_header_can_authenticate() -> None:
    credential = LegacyApiCredentialExtractionService().extract(
        query=ApiParameterMap({"access_token": "query-a"}),
        form=ApiParameterMap({"access_token": ""}),
        authorization=AuthorizationHeader("Bearer header-b"),
        server_authorization=NoAuthorizationHeader(),
    )
    target = _extractor().extract(
        query=ApiParameterMap({"access_token": "query-a"}),
        form=ApiParameterMap({"access_token": ""}),
    )
    assert credential.token.value == "header-b"
    assert type(target).__name__ == "RevokeTargetMissing"


def test_header_only_bearer_is_never_revoke_target() -> None:
    target = _extractor().extract(
        query=ApiParameterMap({}),
        form=ApiParameterMap({}),
    )
    assert type(target).__name__ == "RevokeTargetMissing"
