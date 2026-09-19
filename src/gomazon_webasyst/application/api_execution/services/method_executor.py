from gomazon_webasyst.application.api_execution.composites.invocation import ApiInvocationContext
from gomazon_webasyst.application.api_execution.composites.results import (
    ApiMethodRejected,
    ApiMethodResult,
)
from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod
from gomazon_webasyst.application.api_execution.vo.parameters import ApiRequestParameters
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


class ApiMethodExecutor:
    async def execute(
        self,
        definition: ApiMethodDefinition,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
        http_method: ApiHttpMethod,
    ) -> ApiMethodResult:
        if http_method not in definition.allowed_methods:
            return ApiMethodRejected(
                error=ApiFrameworkError(
                    code=ApiFrameworkErrorCode.INVALID_REQUEST,
                    description=f"Method {http_method.value} not allowed",
                    http_status=405,
                    details={},
                )
            )
        return await definition.handler.execute(context, parameters)
