from hashlib import sha256
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from gomazon_webasyst.application.api_execution.composites.invocation import ApiInvocationRequest
from gomazon_webasyst.application.api_execution.composites.results import ApiExecutionRejected
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod
from gomazon_webasyst.application.api_execution.vo.origin import ApiRequestOrigin
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap, ApiRequestParameters
from gomazon_webasyst.compatibility.webasyst.api.composites.request import LegacyApiHttpRequestComposite
from gomazon_webasyst.compatibility.webasyst.api.composites.response import ApiTransportResponse
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import ApiCredentialMissing
from gomazon_webasyst.compatibility.webasyst.api.services.parameter_decoder import (
    LegacyApiParameterDecoder,
    LegacyApiParameterDecodeRejected,
)
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import ApiHttpsRequired, ApiTransportDisabled
from gomazon_webasyst.compatibility.webasyst.api.services.response_format import ApiResponseFormatRejected
from gomazon_webasyst.compatibility.webasyst.api.services.target_parser import ApiTargetMalformed, ApiTargetReservedEndpoint
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import (
    ApiJsonpCallback,
    AuthorizationHeader,
    NoAuthorizationHeader,
    NoRequestedResponseFormat,
    RequestedResponseFormat,
)
from gomazon_webasyst.composition.api_execution import ApiExecutionComponents
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode, ApiResponseFormat


_HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


def _response(value: ApiTransportResponse) -> Response:
    return Response(
        content=value.body,
        status_code=value.status_code,
        media_type=value.media_type,
        headers=dict(value.headers),
    )


def _rejected(code, description, status, details):
    return ApiExecutionRejected(
        error=ApiFrameworkError(
            code=code,
            description=description,
            http_status=status,
            details=details,
        )
    )


async def _form_parameter_pairs(
    request: Request,
) -> tuple[tuple[str, str], ...]:
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/x-www-form-urlencoded"):
        return ()
    body = (await request.body()).decode("utf-8")
    return tuple(parse_qsl(body, keep_blank_values=True))


def create_legacy_api_router(components: ApiExecutionComponents) -> APIRouter:
    router = APIRouter()
    parameter_decoder = LegacyApiParameterDecoder()

    async def execute(request: Request) -> Response:
        query_result = parameter_decoder.decode(
            tuple(request.query_params.multi_items())
        )
        if isinstance(query_result, LegacyApiParameterDecodeRejected):
            return _response(
                components.response_renderer.render(
                    _rejected(
                        ApiFrameworkErrorCode.INVALID_REQUEST,
                        "Invalid API parameters",
                        400,
                        {
                            "reason": query_result.reason.value,
                            "key": query_result.key,
                        },
                    ),
                    ApiResponseFormat.JSON,
                    ApiJsonpCallback(""),
                )
            )
        query = query_result.parameters

        form_result = parameter_decoder.decode(
            await _form_parameter_pairs(request)
        )
        if isinstance(form_result, LegacyApiParameterDecodeRejected):
            return _response(
                components.response_renderer.render(
                    _rejected(
                        ApiFrameworkErrorCode.INVALID_REQUEST,
                        "Invalid API parameters",
                        400,
                        {
                            "reason": form_result.reason.value,
                            "key": form_result.key,
                        },
                    ),
                    ApiResponseFormat.JSON,
                    ApiJsonpCallback(""),
                )
            )
        form = form_result.parameters
        authorization_value = request.headers.get("authorization")
        authorization = (
            AuthorizationHeader(authorization_value)
            if authorization_value is not None
            else NoAuthorizationHeader()
        )
        server_authorization = (
            AuthorizationHeader(str(request.scope["HTTP_AUTHORIZATION"]))
            if "HTTP_AUTHORIZATION" in request.scope
            else NoAuthorizationHeader()
        )
        transport = LegacyApiHttpRequestComposite(
            request_path=request.url.path.lstrip("/"),
            query=query,
            form=form,
            authorization_header=authorization,
            server_authorization=server_authorization,
            http_method=ApiHttpMethod(request.method),
            is_https=request.url.scheme.lower() == "https",
            requested_format=(
                RequestedResponseFormat(str(query["format"]))
                if "format" in query and str(query["format"]) not in {"", "0"}
                else NoRequestedResponseFormat()
            ),
            callback=ApiJsonpCallback(
                str(query["callback"]) if "callback" in query else ""
            ),
        )
        format_result = components.response_format_service.resolve(
            transport.requested_format
        )
        response_format = (
            ApiResponseFormat.JSON
            if isinstance(format_result, ApiResponseFormatRejected)
            else format_result.format
        )

        precondition = components.preconditions.evaluate(
            is_https=transport.is_https
        )
        if isinstance(precondition, ApiTransportDisabled):
            return _response(
                components.response_renderer.render(
                    _rejected(
                        ApiFrameworkErrorCode.DISABLED,
                        precondition.message,
                        404,
                        {},
                    ),
                    response_format,
                    transport.callback,
                )
            )
        if isinstance(precondition, ApiHttpsRequired):
            return RedirectResponse(
                url=str(request.url.replace(scheme="https")),
                status_code=301,
            )

        if isinstance(format_result, ApiResponseFormatRejected):
            return _response(
                components.response_renderer.render(
                    ApiExecutionRejected(error=format_result.error),
                    ApiResponseFormat.JSON,
                    transport.callback,
                )
            )

        target_result = components.target_parser.parse(
            transport.request_path,
            transport.query,
        )
        if isinstance(target_result, ApiTargetMalformed):
            return _response(
                components.response_renderer.render(
                    _rejected(
                        ApiFrameworkErrorCode.INVALID_REQUEST,
                        "Malformed request or server misconfiguration",
                        400,
                        {},
                    ),
                    response_format,
                    transport.callback,
                )
            )
        if isinstance(target_result, ApiTargetReservedEndpoint):
            return _response(
                components.response_renderer.render(
                    _rejected(
                        ApiFrameworkErrorCode.INVALID_REQUEST,
                        "Reserved API endpoint is not implemented by method execution",
                        404,
                        {"endpoint": target_result.endpoint},
                    ),
                    response_format,
                    transport.callback,
                )
            )

        credential = components.credential_extractor.extract(
            query=transport.query,
            form=transport.form,
            authorization=transport.authorization_header,
            server_authorization=transport.server_authorization,
        )
        if isinstance(credential, ApiCredentialMissing):
            return _response(
                components.response_renderer.render(
                    _rejected(
                        ApiFrameworkErrorCode.TOKEN_REQUIRED,
                        "Access token is missing",
                        400,
                        {},
                    ),
                    response_format,
                    transport.callback,
                )
            )

        result = await components.pipeline(
            ApiInvocationRequest(
                access_token=credential.token,
                target=target_result.target,
                http_method=transport.http_method,
                parameters=ApiRequestParameters(
                    query=transport.query,
                    form=transport.form,
                ),
                origin=ApiRequestOrigin(str(request.base_url)),
            )
        )
        if (
            isinstance(result, ApiExecutionRejected)
            and result.error.code is ApiFrameworkErrorCode.INVALID_TOKEN
            and result.error.details.get("_credential_reason") == "missing"
        ):
            result = ApiExecutionRejected(
                error=ApiFrameworkError(
                    code=result.error.code,
                    description=result.error.description,
                    http_status=result.error.http_status,
                    details={"sha256": sha256(credential.token.value.encode()).hexdigest()},
                )
            )
        return _response(
            components.response_renderer.render(
                result,
                response_format,
                transport.callback,
            )
        )

    @router.api_route("/api.php", methods=_HTTP_METHODS)
    async def api_root(request: Request) -> Response:
        return await execute(request)

    @router.api_route("/api.php/{api_path:path}", methods=_HTTP_METHODS)
    async def api_path(request: Request, api_path: str) -> Response:
        return await execute(request)

    return router
