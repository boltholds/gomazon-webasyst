import json
from dataclasses import FrozenInstanceError

import pytest
from pydantic import TypeAdapter

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiAccessToken, ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.vo.errors import ApiApplicationErrorCode
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodName, ApiMethodTarget
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap, ApiRequestParameters
from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
    ApiInvocationRequest,
    ApiPrincipalContext,
)
from gomazon_webasyst.contracts.api_execution import (
    ApiExecutionRejected,
    ApiExecutionResult,
    ApiFrameworkError,
)
from gomazon_webasyst.contracts.enums import (
    ApiExecutionResultKind,
    ApiFrameworkErrorCode,
    ApiResponseFormat,
    EnumStr,
)


class StubHandler:
    async def execute(self, context, parameters):
        raise AssertionError("handler execution is not part of type tests")


def test_api_http_method_is_open_uppercase_vo() -> None:
    assert ApiHttpMethod("get") == ApiHttpMethod("GET")
    assert ApiHttpMethod("PROPFIND").value == "PROPFIND"
    with pytest.raises(ValueError):
        ApiHttpMethod("bad method")


def test_method_name_and_application_error_code_are_open_frozen_values() -> None:
    method = ApiMethodName("order.get")
    code = ApiApplicationErrorCode("order_not_found")
    assert {method, code}
    with pytest.raises(FrozenInstanceError):
        method.value = "other"  # type: ignore[misc]


def test_method_definition_requires_identity_and_allowed_methods() -> None:
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
    query = ApiParameterMap({"id": "query", "nested": {"items": [1, 2]}})
    form = ApiParameterMap({"id": "form"})
    params = ApiRequestParameters(query=query, form=form)
    assert params.query["id"] == "query"
    assert params.form["id"] == "form"
    assert params.query["nested"] == {"items": (1, 2)}
    with pytest.raises(TypeError):
        params.query.values["id"] = "mutated"  # type: ignore[index]


def test_invocation_composites_reuse_existing_credential_values() -> None:
    target = ApiMethodTarget(AppId("shop"), ApiMethodName("ping"))
    principal = ApiPrincipalContext(
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop"),
    )
    context = ApiInvocationContext(principal=principal, target=target)
    request = ApiInvocationRequest(
        access_token=ApiAccessToken("a" * 32),
        target=target,
        http_method=ApiHttpMethod("get"),
        parameters=ApiRequestParameters(
            query=ApiParameterMap({}),
            form=ApiParameterMap({}),
        ),
    )
    assert context.target == request.target
    assert request.http_method == ApiHttpMethod("GET")


def test_closed_api_execution_domains_are_enumstr() -> None:
    for enum_type in (ApiResponseFormat, ApiFrameworkErrorCode, ApiExecutionResultKind):
        assert issubclass(enum_type, EnumStr)


def test_execution_result_discriminator_accepts_raw_string_and_serializes_string() -> None:
    adapter = TypeAdapter(ApiExecutionResult)
    value = adapter.validate_python(
        {
            "kind": "rejected",
            "error": {
                "code": "invalid_request",
                "description": "bad request",
                "http_status": 400,
                "details": {},
            },
        }
    )
    assert isinstance(value, ApiExecutionRejected)
    assert value.kind is ApiExecutionResultKind.REJECTED
    assert value.error.code is ApiFrameworkErrorCode.INVALID_REQUEST
    assert json.loads(adapter.dump_json(value))["kind"] == "rejected"


def test_framework_error_is_frozen_and_requires_http_status() -> None:
    error = ApiFrameworkError(
        code=ApiFrameworkErrorCode.INVALID_METHOD,
        description="missing",
        http_status=404,
        details={},
    )
    assert error.http_status == 404
