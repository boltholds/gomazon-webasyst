from gomazon_webasyst.application.api_execution.composites.authorization import (
    ApiAuthorizationGranted,
    ApiAuthorizationRejected,
    ApiAuthorizationResult,
)
from gomazon_webasyst.application.api_execution.composites.invocation import ApiPrincipalContext
from gomazon_webasyst.application.api_execution.vo.method import ApiMethodTarget
from gomazon_webasyst.application.ports.api_app_access import ApiAppAccessGranted, ApiAppAccessPolicy
from gomazon_webasyst.application.ports.app_license import AppLicenseBlocked, AppLicensePolicy
from gomazon_webasyst.application.ports.application_registry import (
    ApplicationEnabled,
    ApplicationRegistry,
)
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


class ApiRequestAuthorizer:
    def __init__(
        self,
        *,
        application_registry: ApplicationRegistry,
        app_access: ApiAppAccessPolicy,
        license_policy: AppLicensePolicy,
    ) -> None:
        self._application_registry = application_registry
        self._app_access = app_access
        self._license_policy = license_policy

    async def authorize(
        self,
        principal: ApiPrincipalContext,
        target: ApiMethodTarget,
    ) -> ApiAuthorizationResult:
        application = self._application_registry.resolve_app(target.app_id)
        if not isinstance(application, ApplicationEnabled):
            return ApiAuthorizationRejected(
                error=ApiFrameworkError(
                    code=ApiFrameworkErrorCode.APP_NOT_INSTALLED,
                    description="Application is not installed",
                    http_status=400,
                    details={"app": target.app_id.value},
                )
            )

        access = await self._app_access.authorize(principal.contact_id, target.app_id)
        if not isinstance(access, ApiAppAccessGranted):
            return ApiAuthorizationRejected(
                error=ApiFrameworkError(
                    code=ApiFrameworkErrorCode.ACCESS_DENIED,
                    description="Access denied",
                    http_status=403,
                    details={"app": target.app_id.value},
                )
            )

        if target.app_id not in principal.scope.apps:
            return ApiAuthorizationRejected(
                error=ApiFrameworkError(
                    code=ApiFrameworkErrorCode.ACCESS_DENIED,
                    description="Application is outside token scope",
                    http_status=403,
                    details={"app": target.app_id.value},
                )
            )

        license_decision = await self._license_policy.check(target.app_id)
        if isinstance(license_decision, AppLicenseBlocked):
            return ApiAuthorizationRejected(
                error=ApiFrameworkError(
                    code=ApiFrameworkErrorCode.PAYMENT_REQUIRED,
                    description="Application license is required",
                    http_status=402,
                    details={"app": target.app_id.value},
                )
            )
        return ApiAuthorizationGranted()
