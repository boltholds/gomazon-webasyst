from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import SecretStr

from gomazon_webasyst.application.api_execution.composites.results import (
    ApiExecutionRejected,
)
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.application.oauth_authorization.composites.revoke_authentication import (
    OAuthRevokeAuthenticated,
    OAuthRevokeAuthenticationRejected,
)
from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendCurrentSubjectRequest,
    BackendLogoutRequest,
    BackendPasswordLoginRequest,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectMissing,
    OAuthRedirectProvided,
)
from gomazon_webasyst.application.ports.oauth_redirect_policy import (
    OAuthRedirectAccepted,
    OAuthRedirectRejected,
)
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import (
    ApiCredentialMissing,
)
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import (
    ApiHttpsRequired,
    ApiTransportDisabled,
)
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import (
    ApiJsonpCallback,
    AuthorizationHeader,
    NoAuthorizationHeader,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.cancel import (
    OAuthCancelFrameworkError,
    OAuthCancelRedirect,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.controller_format import (
    OAuthControllerFormatRejected,
    OAuthControllerFormatResolved,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.csrf import (
    OAuthCsrfAccepted,
    OAuthCsrfCookieMissing,
    OAuthCsrfCookieProvided,
    OAuthCsrfFormMissing,
    OAuthCsrfFormProvided,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.deny import (
    OAuthDenyHtmlError,
    OAuthDenyRedirect,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.html_renderer import (
    ConsentAppView,
    OAuthCodePageModel,
    OAuthConsentPageModel,
    OAuthErrorPageModel,
    OAuthLoginPageModel,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.request_validation import (
    OAuthAuthorizationRequestParsed,
    OAuthAuthorizationRequestRejected,
)
from gomazon_webasyst.compatibility.webasyst.oauth.vo.transport import (
    LegacyOAuthCancelRequest,
)
from gomazon_webasyst.composition.oauth_authorization import OAuthAuthorizationComponents
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.auth import (
    BackendPasswordCredentials,
    LoginPolicyContext,
)
from gomazon_webasyst.contracts.backend_session_bridge import (
    BackendPasswordLoginRejected,
    BackendPasswordLoginSucceeded,
    CurrentBackendSubjectResolved,
    CurrentBackendSubjectUnauthenticated,
)
from gomazon_webasyst.contracts.enums import (
    ApiFrameworkErrorCode,
    ApiResponseFormat,
    OAuthConsentDecision,
    RememberIntent,
)
from gomazon_webasyst.compatibility.webasyst.oauth.composites.controller_response import (
    OAuthControllerRenderedResponse,
)
from gomazon_webasyst.contracts.oauth_authorization import (
    OAuthAuthorizationCodeGranted,
    OAuthAuthorizationDenied,
    OAuthAuthorizationGrantUnavailable,
    OAuthAuthorizationInvalidScope,
    OAuthConsentRequired,
    OAuthImplicitTokenGranted,
)
from gomazon_webasyst.presentation.http.backend_session import (
    apply_backend_auth_cookie_mutations,
    normalize_backend_auth_request,
)


_HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


def _php_truthy(value) -> bool:
    if value is False or value == 0 or value == 0.0:
        return False
    if isinstance(value, str):
        return value not in {"", "0"}
    if isinstance(value, tuple | dict):
        return len(value) > 0
    return value is not None


async def _form_parameters(request: Request) -> ApiParameterMap:
    if request.method != "POST":
        return ApiParameterMap({})
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/x-www-form-urlencoded"):
        return ApiParameterMap({})
    body = (await request.body()).decode("utf-8")
    return ApiParameterMap(dict(parse_qsl(body, keep_blank_values=True)))


def _request_text(
    form: ApiParameterMap,
    query: ApiParameterMap,
    name: str,
) -> str:
    value = form[name] if name in form else query[name] if name in query else ""
    return value if isinstance(value, str) else str(value)


def _framework_response(
    components: OAuthAuthorizationComponents,
    error: ApiFrameworkError,
    *,
    callback: ApiJsonpCallback = ApiJsonpCallback(""),
) -> Response:
    rendered = components.framework_response_renderer.render(
        ApiExecutionRejected(error=error),
        ApiResponseFormat.JSON,
        callback,
    )
    return Response(
        content=rendered.body,
        status_code=rendered.status_code,
        media_type=rendered.media_type,
        headers=dict(rendered.headers),
    )


def _controller_response(value: OAuthControllerRenderedResponse) -> Response:
    return Response(
        content=value.body,
        status_code=value.status_code,
        media_type=value.media_type,
    )


def _callback(query: ApiParameterMap) -> ApiJsonpCallback:
    value = str(query["callback"]) if "callback" in query else ""
    return ApiJsonpCallback(value)


def _authorization_headers(request: Request):
    raw = request.headers.get("authorization")
    authorization = (
        AuthorizationHeader(raw)
        if raw is not None
        else NoAuthorizationHeader()
    )
    server_authorization = (
        AuthorizationHeader(str(request.scope["HTTP_AUTHORIZATION"]))
        if "HTTP_AUTHORIZATION" in request.scope
        else NoAuthorizationHeader()
    )
    return authorization, server_authorization


def _precondition_response(
    request: Request,
    components: OAuthAuthorizationComponents,
):
    precondition = components.preconditions.evaluate(
        is_https=request.url.scheme.lower() == "https"
    )
    if isinstance(precondition, ApiTransportDisabled):
        return _framework_response(
            components,
            ApiFrameworkError(
                code=ApiFrameworkErrorCode.DISABLED,
                description=precondition.message,
                http_status=404,
                details={},
            ),
        )
    if isinstance(precondition, ApiHttpsRequired):
        return RedirectResponse(
            url=str(request.url.replace(scheme="https")),
            status_code=301,
        )
    return None


def _html(body: str, *, status_code: int = 200) -> Response:
    return Response(
        content=body,
        status_code=status_code,
        media_type="text/html; charset=utf-8",
    )


def _csrf_cookie_state(request: Request):
    if "_csrf" not in request.cookies:
        return OAuthCsrfCookieMissing()
    return OAuthCsrfCookieProvided(request.cookies["_csrf"])


def _csrf_form_state(form: ApiParameterMap):
    if "_csrf" not in form:
        return OAuthCsrfFormMissing()
    return OAuthCsrfFormProvided(str(form["_csrf"]))


def _issue_csrf(
    response: Response,
    request: Request,
    components: OAuthAuthorizationComponents,
):
    issued = components.csrf_service.issue(_csrf_cookie_state(request))
    if issued.set_cookie:
        response.set_cookie(
            key="_csrf",
            value=issued.token.value,
            path="/",
            secure=components.backend_session_bridge.cookie_policy.secure,
            httponly=False,
            samesite="lax",
        )
    return issued.token


def _apply_bridge_dispositions(
    response: Response,
    components: OAuthAuthorizationComponents,
    *,
    session_disposition,
    persistent_disposition,
) -> None:
    mutations = components.backend_session_bridge.cookie_mutation_service.plan(
        session_disposition=session_disposition,
        persistent_disposition=persistent_disposition,
    )
    apply_backend_auth_cookie_mutations(
        response,
        mutations,
        components.backend_session_bridge.cookie_policy,
    )


def _raw_client_name(
    form: ApiParameterMap,
    query: ApiParameterMap,
) -> str:
    return _request_text(form, query, "client_name")


def _login_page(
    request: Request,
    components: OAuthAuthorizationComponents,
    *,
    client_name: str,
    status_code: int = 200,
) -> Response:
    issued = components.csrf_service.issue(_csrf_cookie_state(request))
    response = _html(
        components.html_renderer.login(
            OAuthLoginPageModel(
                client_name=client_name,
                csrf_token=issued.token.value,
                action=str(request.url),
            )
        ),
        status_code=status_code,
    )
    if issued.set_cookie:
        response.set_cookie(
            key="_csrf",
            value=issued.token.value,
            path="/",
            secure=components.backend_session_bridge.cookie_policy.secure,
            httponly=False,
            samesite="lax",
        )
    return response


def _error_page(
    components: OAuthAuthorizationComponents,
    *,
    code: str,
    description: str,
    status_code: int = 200,
) -> Response:
    return _html(
        components.html_renderer.error(
            OAuthErrorPageModel(
                error_code=code,
                description=description,
            )
        ),
        status_code=status_code,
    )


def create_legacy_oauth_router(
    components: OAuthAuthorizationComponents,
) -> APIRouter:
    router = APIRouter()

    @router.api_route("/api.php/auth", methods=["GET", "POST"])
    async def oauth_auth(request: Request) -> Response:
        query = ApiParameterMap(dict(request.query_params))
        form = await _form_parameters(request)

        precondition = components.preconditions.evaluate(
            is_https=request.url.scheme.lower() == "https"
        )
        if isinstance(precondition, ApiTransportDisabled):
            return _framework_response(
                components,
                ApiFrameworkError(
                    code=ApiFrameworkErrorCode.DISABLED,
                    description=precondition.message,
                    http_status=404,
                    details={},
                ),
            )
        if isinstance(precondition, ApiHttpsRequired):
            return RedirectResponse(
                url=str(request.url.replace(scheme="https")),
                status_code=301,
            )

        if (
            request.method == "POST"
            and "cancel" in form
            and _php_truthy(form["cancel"])
        ):
            cancelled = components.cancel_service.cancel(
                LegacyOAuthCancelRequest(
                    raw_response_type=_request_text(
                        form,
                        query,
                        "response_type",
                    ),
                    raw_redirect_uri=_request_text(
                        form,
                        query,
                        "redirect_uri",
                    ),
                    raw_client_name=_raw_client_name(form, query),
                )
            )
            if isinstance(cancelled, OAuthCancelRedirect):
                return RedirectResponse(
                    url=cancelled.location,
                    status_code=302,
                )
            if isinstance(cancelled, OAuthCancelFrameworkError):
                return _framework_response(components, cancelled.error)
            raise AssertionError("unsupported oauth cancel result")

        auth_state = normalize_backend_auth_request(
            request,
            components.backend_session_bridge,
        )
        current = await components.backend_session_bridge.current_subject_flow(
            BackendCurrentSubjectRequest(
                session_credential=auth_state.session_credential,
                persistent_credential=auth_state.persistent_credential,
                session_metadata=auth_state.session_metadata,
                persistent_login_mode=(
                    components.backend_session_bridge.persistent_login_mode
                ),
            )
        )

        if isinstance(current, CurrentBackendSubjectUnauthenticated):
            if request.method == "POST":
                csrf = components.csrf_service.validate(
                    _csrf_cookie_state(request),
                    _csrf_form_state(form),
                )
                if not isinstance(csrf, OAuthCsrfAccepted):
                    response = _login_page(
                        request,
                        components,
                        client_name=_raw_client_name(form, query),
                        status_code=403,
                    )
                    _apply_bridge_dispositions(
                        response,
                        components,
                        session_disposition=current.session_disposition,
                        persistent_disposition=current.persistent_disposition,
                    )
                    return response

                remember = (
                    RememberIntent.PERSIST
                    if "remember" in form and _php_truthy(form["remember"])
                    else RememberIntent.SESSION_ONLY
                )
                identifier = _request_text(form, ApiParameterMap({}), "identifier")
                password = _request_text(form, ApiParameterMap({}), "password")
                login = await components.backend_session_bridge.password_login_flow(
                    BackendPasswordLoginRequest(
                        credentials=BackendPasswordCredentials(
                            identifier=identifier,
                            password=SecretStr(password),
                            login_context=LoginPolicyContext(
                                enabled_schemes=("login",)
                            ),
                            session_metadata=auth_state.session_metadata,
                        ),
                        remember_intent=remember,
                        persistent_login_mode=(
                            components.backend_session_bridge.persistent_login_mode
                        ),
                    )
                )
                if isinstance(login, BackendPasswordLoginSucceeded):
                    response = RedirectResponse(
                        url=str(request.url),
                        status_code=302,
                    )
                    _apply_bridge_dispositions(
                        response,
                        components,
                        session_disposition=current.session_disposition,
                        persistent_disposition=current.persistent_disposition,
                    )
                    _apply_bridge_dispositions(
                        response,
                        components,
                        session_disposition=login.session_disposition,
                        persistent_disposition=login.persistent_disposition,
                    )
                    return response
                if not isinstance(login, BackendPasswordLoginRejected):
                    raise AssertionError("unsupported backend login result")

            response = _login_page(
                request,
                components,
                client_name=_raw_client_name(form, query),
            )
            _apply_bridge_dispositions(
                response,
                components,
                session_disposition=current.session_disposition,
                persistent_disposition=current.persistent_disposition,
            )
            return response

        if not isinstance(current, CurrentBackendSubjectResolved):
            raise AssertionError("unsupported backend current subject result")

        parsed = components.authorization_request_service.parse(query)
        if isinstance(parsed, OAuthAuthorizationRequestRejected):
            response = _error_page(
                components,
                code=parsed.error.code.value,
                description=parsed.error.description,
                status_code=parsed.error.http_status,
            )
            _apply_bridge_dispositions(
                response,
                components,
                session_disposition=current.session_disposition,
                persistent_disposition=current.persistent_disposition,
            )
            return response
        if not isinstance(parsed, OAuthAuthorizationRequestParsed):
            raise AssertionError("unsupported oauth authorization request result")

        redirect_decision = components.redirect_policy.validate(
            parsed.request.client_id,
            parsed.request.redirect_target,
        )
        if isinstance(redirect_decision, OAuthRedirectRejected):
            response = _error_page(
                components,
                code="invalid_request",
                description=redirect_decision.reason,
                status_code=400,
            )
            _apply_bridge_dispositions(
                response,
                components,
                session_disposition=current.session_disposition,
                persistent_disposition=current.persistent_disposition,
            )
            return response
        if not isinstance(redirect_decision, OAuthRedirectAccepted):
            raise AssertionError("unsupported oauth redirect decision")

        if request.method == "POST":
            csrf = components.csrf_service.validate(
                _csrf_cookie_state(request),
                _csrf_form_state(form),
            )
            if not isinstance(csrf, OAuthCsrfAccepted):
                response = _error_page(
                    components,
                    code="invalid_request",
                    description="Invalid CSRF token",
                    status_code=403,
                )
                _apply_bridge_dispositions(
                    response,
                    components,
                    session_disposition=current.session_disposition,
                    persistent_disposition=current.persistent_disposition,
                )
                return response

            if "logout" in form and _php_truthy(form["logout"]):
                logout = await components.backend_session_bridge.logout_flow(
                    BackendLogoutRequest(
                        session_credential=auth_state.session_credential
                    )
                )
                response = RedirectResponse(
                    url=str(request.url),
                    status_code=302,
                )
                _apply_bridge_dispositions(
                    response,
                    components,
                    session_disposition=current.session_disposition,
                    persistent_disposition=current.persistent_disposition,
                )
                _apply_bridge_dispositions(
                    response,
                    components,
                    session_disposition=logout.session_disposition,
                    persistent_disposition=logout.persistent_disposition,
                )
                return response

            decision = (
                OAuthConsentDecision.APPROVE
                if "approve" in form and _php_truthy(form["approve"])
                else OAuthConsentDecision.DENY
            )
            result = await components.authorization_flow.decide(
                current.subject,
                parsed.request,
                decision,
            )
        else:
            result = await components.authorization_flow.prepare(
                current.subject,
                parsed.request,
            )

        if isinstance(result, OAuthConsentRequired):
            issued = components.csrf_service.issue(_csrf_cookie_state(request))
            response = _html(
                components.html_renderer.consent(
                    OAuthConsentPageModel(
                        client_name=result.client_name.value,
                        applications=tuple(
                            ConsentAppView(
                                app_id=app.app_id.value,
                                name=app.display_name.value,
                                icon=app.icon.value,
                            )
                            for app in result.applications
                        ),
                        csrf_token=issued.token.value,
                        action=str(request.url),
                    )
                )
            )
            if issued.set_cookie:
                response.set_cookie(
                    key="_csrf",
                    value=issued.token.value,
                    path="/",
                    secure=components.backend_session_bridge.cookie_policy.secure,
                    httponly=False,
                    samesite="lax",
                )
        elif isinstance(result, OAuthAuthorizationCodeGranted):
            if isinstance(result.redirect_target, OAuthRedirectProvided):
                response = RedirectResponse(
                    url=components.redirect_service.code(
                        result.redirect_target.uri,
                        result.code,
                    ).location,
                    status_code=302,
                )
            elif isinstance(result.redirect_target, OAuthRedirectMissing):
                response = _html(
                    components.html_renderer.code(
                        OAuthCodePageModel(code=result.code.value)
                    )
                )
            else:
                raise AssertionError("unsupported oauth redirect target")
        elif isinstance(result, OAuthImplicitTokenGranted):
            if not isinstance(result.redirect_target, OAuthRedirectProvided):
                raise AssertionError("implicit token grant requires redirect")
            response = RedirectResponse(
                url=components.redirect_service.token(
                    result.redirect_target.uri,
                    result.access_token.value,
                ).location,
                status_code=302,
            )
        elif isinstance(result, OAuthAuthorizationDenied):
            denied = components.deny_service.deny(parsed.request)
            if isinstance(denied, OAuthDenyRedirect):
                response = RedirectResponse(
                    url=denied.location,
                    status_code=302,
                )
            elif isinstance(denied, OAuthDenyHtmlError):
                response = _error_page(
                    components,
                    code=denied.error_code,
                    description=denied.description,
                )
            else:
                raise AssertionError("unsupported oauth denial result")
        elif isinstance(result, OAuthAuthorizationInvalidScope):
            response = _error_page(
                components,
                code="invalid_request",
                description="Invalid scope",
                status_code=400,
            )
        elif isinstance(result, OAuthAuthorizationGrantUnavailable):
            response = _error_page(
                components,
                code="invalid_request",
                description="Authorization grant unavailable",
                status_code=500,
            )
        else:
            raise AssertionError("unsupported oauth authorization result")

        _apply_bridge_dispositions(
            response,
            components,
            session_disposition=current.session_disposition,
            persistent_disposition=current.persistent_disposition,
        )
        return response


    @router.api_route("/api.php/token", methods=_HTTP_METHODS)
    async def oauth_token(request: Request) -> Response:
        precondition_response = _precondition_response(request, components)
        if precondition_response is not None:
            return precondition_response

        query = ApiParameterMap(dict(request.query_params))
        form = await _form_parameters(request)
        format_result = components.controller_format_service.resolve(query)
        if isinstance(format_result, OAuthControllerFormatRejected):
            return _controller_response(
                components.controller_renderer.render(
                    payload=format_result.payload,
                    response_format=format_result.format,
                )
            )
        if not isinstance(format_result, OAuthControllerFormatResolved):
            raise AssertionError("unsupported oauth controller format result")

        result = await components.token_controller.execute(
            ApiRequestParameters(query=query, form=form),
            format_result.format,
        )
        return _controller_response(
            components.controller_renderer.render(
                payload=result.payload,
                response_format=result.format,
            )
        )

    @router.api_route("/api.php/revoke", methods=_HTTP_METHODS)
    async def oauth_revoke(request: Request) -> Response:
        precondition_response = _precondition_response(request, components)
        if precondition_response is not None:
            return precondition_response

        query = ApiParameterMap(dict(request.query_params))
        form = await _form_parameters(request)
        authorization, server_authorization = _authorization_headers(request)
        credential = components.credential_extractor.extract(
            query=query,
            form=form,
            authorization=authorization,
            server_authorization=server_authorization,
        )
        callback = _callback(query)
        if isinstance(credential, ApiCredentialMissing):
            return _framework_response(
                components,
                ApiFrameworkError(
                    code=ApiFrameworkErrorCode.TOKEN_REQUIRED,
                    description="Access token is missing",
                    http_status=400,
                    details={},
                ),
                callback=callback,
            )

        authenticated = await components.revoke_authentication_flow.authenticate(
            credential.token
        )
        if isinstance(authenticated, OAuthRevokeAuthenticationRejected):
            return _framework_response(
                components,
                ApiFrameworkError(
                    code=ApiFrameworkErrorCode.INVALID_TOKEN,
                    description="Invalid access token",
                    http_status=401,
                    details={},
                ),
                callback=callback,
            )
        if not isinstance(authenticated, OAuthRevokeAuthenticated):
            raise AssertionError("unsupported oauth revoke authentication result")

        format_result = components.controller_format_service.resolve(query)
        if isinstance(format_result, OAuthControllerFormatRejected):
            return _controller_response(
                components.controller_renderer.render(
                    payload=format_result.payload,
                    response_format=format_result.format,
                )
            )
        if not isinstance(format_result, OAuthControllerFormatResolved):
            raise AssertionError("unsupported oauth controller format result")

        target = components.revoke_target_extractor.extract(
            query=query,
            form=form,
        )
        result = await components.revoke_controller.execute(
            target,
            format_result.format,
        )
        return _controller_response(
            components.controller_renderer.render(
                payload=result.payload,
                response_format=result.format,
            )
        )

    return router
