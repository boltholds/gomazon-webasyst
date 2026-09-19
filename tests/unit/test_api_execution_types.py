import pytest
from pydantic import TypeAdapter

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiAccessToken, ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodName, ApiMethodTarget
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap, ApiRequestParameters
from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
    ApiInvocationRequest,
    ApiPrincipalContext,
)
from gomazon_webasyst.application.api_execution.composites.results import (
    ApiExecutionRejected,
    ApiExecutionResult,
)
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


class StubHandler:
    async def execute(self, context, parameters):
        raise AssertionError("not called")


def test_api_http_method_is_open_uppercase_vo() -> None:
    assert ApiHttpMethod("get") == ApiHttpMethod("GET")
    assert ApiHttpMethod("PROPFIND").value == "PROPFIND"
    with pytest.raises(ValueError):
        ApiHttpMethod("bad method")


def test_method_definition_requires_nonempty_allowed_methods() -> None:
    target = ApiMethodTarget(AppId("shop"), ApiMethodName("order.get"))
    definition = ApiMethodDefinition(
        target=target,
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=StubHandler(),
    )
    assert definition.target == target
    with pytest.raises(ValueError):
        ApiMethodDefinition(target=target, allowed_methods=frozenset(), handler=StubHandler())


def test_request_parameters_preserve_sources_and_are_immutable() -> None:
    source = {"id": "query"}
    params = ApiRequestParameters(
        query=ApiParameterMap(source),
        form=ApiParameterMap({"id": "form"}),
    )
    source["id"] = "changed"
    assert params.query["id"] == "query"
    assert params.form["id"] == "form"
    with pytest.raises(TypeError):
        params.query.values["id"] = "mutated"


def test_invocation_composites_reuse_existing_credential_values() -> None:
    target = ApiMethodTarget(AppId("shop"), ApiMethodName("ping"))
    request = ApiInvocationRequest(
        access_token=ApiAccessToken("a" * 32),
        target=target,
        http_method=ApiHttpMethod("GET"),
        parameters=ApiRequestParameters(ApiParameterMap({}), ApiParameterMap({})),
    )
    principal = ApiPrincipalContext(
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop"),
    )
    context = ApiInvocationContext(principal=principal, target=target)
    assert request.target == context.target


def test_execution_result_serializes_closed_enumstr_code() -> None:
    result = ApiExecutionRejected(
        error=ApiFrameworkError(
            code=ApiFrameworkErrorCode.INVALID_METHOD,
            description="Invalid method",
            http_status=404,
            details={},
        )
    )
    adapter = TypeAdapter(ApiExecutionResult)
    payload = adapter.dump_python(result, mode="json")
    assert payload["error"]["code"] == "invalid_method"
    restored = adapter.validate_python(payload)
    assert restored == result


def test_execution_payload_rejects_non_json_python_objects() -> None:
    class NotJson:
        pass

    with pytest.raises(Exception):
        from gomazon_webasyst.contracts.api_execution import ApiMethodSucceeded
        ApiMethodSucceeded(payload=NotJson(), status_code=200)


def test_framework_error_details_reject_non_json_python_objects() -> None:
    with pytest.raises(Exception):
        ApiFrameworkError(
            code=ApiFrameworkErrorCode.INVALID_REQUEST,
            description="bad",
            http_status=400,
            details={"bad": object()},
        )
