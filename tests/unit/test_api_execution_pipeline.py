import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiAccessToken, ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.composites.authorization import ApiAuthorizationGranted, ApiAuthorizationRejected
from gomazon_webasyst.application.api_execution.composites.invocation import ApiInvocationRequest
from gomazon_webasyst.application.api_execution.composites.pipeline import ApiExecutionPipeline
from gomazon_webasyst.application.api_execution.composites.results import (
    ApiExecutionRejected,
    ApiExecutionSucceeded,
    ApiMethodSucceeded,
)
from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.services.activity import ApiActivitySkipped
from gomazon_webasyst.application.api_execution.vo.origin import ApiRequestOrigin
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodName, ApiMethodTarget
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap, ApiRequestParameters
from gomazon_webasyst.application.ports.api_method_registry import ApiMethodMissing, ApiMethodResolved
from gomazon_webasyst.contracts.api_credentials import ApiAccessTokenResolved, ApiAccessTokenResolveRejected
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiAccessTokenResolveRejectReason, ApiFrameworkErrorCode


TOKEN = ApiAccessToken("a" * 32)
TARGET = ApiMethodTarget(AppId("shop"), ApiMethodName("ping"))
REQUEST = ApiInvocationRequest(
    access_token=TOKEN,
    target=TARGET,
    http_method=ApiHttpMethod("GET"),
    parameters=ApiRequestParameters(ApiParameterMap({}), ApiParameterMap({})),
    origin=ApiRequestOrigin("https://example.test/"),
)


class StubHandler:
    async def execute(self, context, parameters):
        return ApiMethodSucceeded(payload={"ok": True}, status_code=200)


DEFINITION = ApiMethodDefinition(
    target=TARGET,
    allowed_methods=frozenset({ApiHttpMethod("GET")}),
    handler=StubHandler(),
)


class TokenResolver:
    def __init__(self, log, result):
        self.log, self.result = log, result
    async def __call__(self, token):
        self.log.append("token")
        return self.result


class Activity:
    def __init__(self, log):
        self.log = log
    async def touch_if_due(self, contact_id):
        self.log.append("activity")
        return ApiActivitySkipped(contact_id)


class Authorizer:
    def __init__(self, log, result):
        self.log, self.result = log, result
    async def authorize(self, principal, target):
        self.log.append("authorize")
        return self.result


class Registry:
    def __init__(self, log, result):
        self.log, self.result = log, result
    def resolve(self, target):
        self.log.append("registry")
        return self.result


class Executor:
    def __init__(self, log, result):
        self.log, self.result = log, result
    async def execute(self, definition, context, parameters, http_method):
        self.log.append("execute")
        return self.result


def resolved():
    from gomazon_webasyst.contracts.api_credentials import ApiTokenLastUsedAt
    from datetime import datetime
    return ApiAccessTokenResolved(
        access_token=TOKEN,
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop"),
        last_use=ApiTokenLastUsedAt(at=datetime(2026, 9, 19, 12, 0, 0)),
    )


@pytest.mark.asyncio
async def test_pipeline_sequences_token_activity_authorization_registry_executor() -> None:
    log = []
    pipeline = ApiExecutionPipeline(
        resolve_access_token=TokenResolver(log, resolved()),
        activity_service=Activity(log),
        authorizer=Authorizer(log, ApiAuthorizationGranted()),
        method_registry=Registry(log, ApiMethodResolved(definition=DEFINITION)),
        method_executor=Executor(log, ApiMethodSucceeded(payload={"ok": True}, status_code=200)),
    )
    result = await pipeline(REQUEST)
    assert isinstance(result, ApiExecutionSucceeded)
    assert result.payload == {"ok": True}
    assert log == ["token", "activity", "authorize", "registry", "execute"]


@pytest.mark.asyncio
async def test_token_rejection_stops_every_later_stage() -> None:
    log = []
    pipeline = ApiExecutionPipeline(
        resolve_access_token=TokenResolver(
            log,
            ApiAccessTokenResolveRejected(reason=ApiAccessTokenResolveRejectReason.MISSING),
        ),
        activity_service=Activity(log),
        authorizer=Authorizer(log, ApiAuthorizationGranted()),
        method_registry=Registry(log, ApiMethodResolved(definition=DEFINITION)),
        method_executor=Executor(log, ApiMethodSucceeded(payload={}, status_code=200)),
    )
    result = await pipeline(REQUEST)
    assert isinstance(result, ApiExecutionRejected)
    assert result.error.code is ApiFrameworkErrorCode.INVALID_TOKEN
    assert log == ["token"]


@pytest.mark.asyncio
async def test_authorization_rejection_stops_registry_and_executor() -> None:
    log = []
    rejection = ApiAuthorizationRejected(
        error=ApiFrameworkError(
            code=ApiFrameworkErrorCode.ACCESS_DENIED,
            description="Access denied",
            http_status=403,
            details={},
        )
    )
    pipeline = ApiExecutionPipeline(
        resolve_access_token=TokenResolver(log, resolved()),
        activity_service=Activity(log),
        authorizer=Authorizer(log, rejection),
        method_registry=Registry(log, ApiMethodResolved(definition=DEFINITION)),
        method_executor=Executor(log, ApiMethodSucceeded(payload={}, status_code=200)),
    )
    result = await pipeline(REQUEST)
    assert isinstance(result, ApiExecutionRejected)
    assert result.error.code is ApiFrameworkErrorCode.ACCESS_DENIED
    assert log == ["token", "activity", "authorize"]


@pytest.mark.asyncio
async def test_registry_miss_maps_invalid_method_without_executor() -> None:
    log = []
    pipeline = ApiExecutionPipeline(
        resolve_access_token=TokenResolver(log, resolved()),
        activity_service=Activity(log),
        authorizer=Authorizer(log, ApiAuthorizationGranted()),
        method_registry=Registry(log, ApiMethodMissing(target=TARGET)),
        method_executor=Executor(log, ApiMethodSucceeded(payload={}, status_code=200)),
    )
    result = await pipeline(REQUEST)
    assert isinstance(result, ApiExecutionRejected)
    assert result.error.code is ApiFrameworkErrorCode.INVALID_METHOD
    assert log == ["token", "activity", "authorize", "registry"]
