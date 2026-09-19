from typing import Protocol

from gomazon_webasyst.application.api_execution.composites.invocation import ApiInvocationContext
from gomazon_webasyst.application.api_execution.composites.results import ApiMethodResult
from gomazon_webasyst.application.api_execution.vo.parameters import ApiRequestParameters


class ApiMethodHandler(Protocol):
    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ) -> ApiMethodResult: ...
