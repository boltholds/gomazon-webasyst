from gomazon_webasyst.application.api_execution.composites.authorization import ApiAuthorizationRejected
from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
    ApiInvocationRequest,
    ApiPrincipalContext,
)
from gomazon_webasyst.application.api_execution.composites.results import (
    ApiExecutionRejected,
    ApiExecutionResult,
    ApiExecutionSucceeded,
    ApiMethodRejected,
    ApiMethodSucceeded,
)
from gomazon_webasyst.application.api_execution.services.activity import ApiUserActivityService
from gomazon_webasyst.application.api_execution.services.authorizer import ApiRequestAuthorizer
from gomazon_webasyst.application.api_execution.services.method_executor import ApiMethodExecutor
from gomazon_webasyst.application.api_credentials import ResolveApiAccessToken
from gomazon_webasyst.application.ports.api_method_registry import (
    ApiMethodMissing,
    ApiMethodRegistry,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenResolved,
    ApiAccessTokenResolveRejected,
)
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


class ApiExecutionPipeline:
    def __init__(
        self,
        *,
        resolve_access_token: ResolveApiAccessToken,
        activity_service: ApiUserActivityService,
        authorizer: ApiRequestAuthorizer,
        method_registry: ApiMethodRegistry,
        method_executor: ApiMethodExecutor,
    ) -> None:
        self._resolve_access_token = resolve_access_token
        self._activity_service = activity_service
        self._authorizer = authorizer
        self._method_registry = method_registry
        self._method_executor = method_executor

    async def __call__(self, request: ApiInvocationRequest) -> ApiExecutionResult:
        token_result = await self._resolve_access_token(request.access_token)
        if isinstance(token_result, ApiAccessTokenResolveRejected):
            return ApiExecutionRejected(
                error=ApiFrameworkError(
                    code=ApiFrameworkErrorCode.INVALID_TOKEN,
                    description="Invalid access token",
                    http_status=401,
                    details={},
                )
            )
        if not isinstance(token_result, ApiAccessTokenResolved):
            raise AssertionError("unsupported API access token result")

        principal = ApiPrincipalContext(
            contact_id=token_result.contact_id,
            client_id=token_result.client_id,
            scope=token_result.scope,
        )

        await self._activity_service.touch_if_due(principal.contact_id)

        authorization = await self._authorizer.authorize(principal, request.target)
        if isinstance(authorization, ApiAuthorizationRejected):
            return ApiExecutionRejected(error=authorization.error)

        resolved_method = self._method_registry.resolve(request.target)
        if isinstance(resolved_method, ApiMethodMissing):
            return ApiExecutionRejected(
                error=ApiFrameworkError(
                    code=ApiFrameworkErrorCode.INVALID_METHOD,
                    description="Invalid API method",
                    http_status=404,
                    details={
                        "app": request.target.app_id.value,
                        "method": request.target.method.value,
                    },
                )
            )

        context = ApiInvocationContext(
            principal=principal,
            target=request.target,
        )
        method_result = await self._method_executor.execute(
            resolved_method.definition,
            context,
            request.parameters,
            request.http_method,
        )
        if isinstance(method_result, ApiMethodRejected):
            return ApiExecutionRejected(error=method_result.error)
        if isinstance(method_result, ApiMethodSucceeded):
            return ApiExecutionSucceeded(
                payload=method_result.payload,
                status_code=method_result.status_code,
            )
        raise AssertionError("unsupported API method result")
