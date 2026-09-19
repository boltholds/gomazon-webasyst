import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.composites.invocation import ApiInvocationContext, ApiPrincipalContext
from gomazon_webasyst.application.api_execution.composites.results import ApiMethodRejected, ApiMethodSucceeded
from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.services.method_executor import ApiMethodExecutor
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodName, ApiMethodTarget
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap, ApiRequestParameters
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


TARGET = ApiMethodTarget(AppId("shop"), ApiMethodName("ping"))
CONTEXT = ApiInvocationContext(
    principal=ApiPrincipalContext(42, ApiClientId("client"), ApiScope.of("shop")),
    target=TARGET,
)
PARAMETERS = ApiRequestParameters(ApiParameterMap({}), ApiParameterMap({}))


class RecordingHandler:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, context, parameters):
        self.calls.append((context, parameters))
        return ApiMethodSucceeded(payload={"ok": True}, status_code=200)


@pytest.mark.asyncio
async def test_executor_rejects_unknown_extension_verb_before_handler_call() -> None:
    handler = RecordingHandler()
    definition = ApiMethodDefinition(
        target=TARGET,
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=handler,
    )

    result = await ApiMethodExecutor().execute(
        definition,
        CONTEXT,
        PARAMETERS,
        ApiHttpMethod("PROPFIND"),
    )

    assert isinstance(result, ApiMethodRejected)
    assert result.error.code is ApiFrameworkErrorCode.INVALID_REQUEST
    assert result.error.http_status == 405
    assert handler.calls == []


@pytest.mark.asyncio
async def test_executor_allows_any_registered_allowed_verb_and_delegates_once() -> None:
    handler = RecordingHandler()
    definition = ApiMethodDefinition(
        target=TARGET,
        allowed_methods=frozenset({ApiHttpMethod("GET"), ApiHttpMethod("POST")}),
        handler=handler,
    )

    result = await ApiMethodExecutor().execute(
        definition,
        CONTEXT,
        PARAMETERS,
        ApiHttpMethod("post"),
    )

    assert isinstance(result, ApiMethodSucceeded)
    assert result.payload == {"ok": True}
    assert handler.calls == [(CONTEXT, PARAMETERS)]
