import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.composites.authorization import ApiAuthorizationGranted, ApiAuthorizationRejected
from gomazon_webasyst.application.api_execution.composites.invocation import ApiPrincipalContext
from gomazon_webasyst.application.api_execution.services.authorizer import ApiRequestAuthorizer
from gomazon_webasyst.application.api_execution.vo.method import ApiMethodName, ApiMethodTarget
from gomazon_webasyst.application.ports.api_app_access import ApiAppAccessDenied, ApiAppAccessGranted
from gomazon_webasyst.application.ports.app_license import AppLicenseBlocked, AppLicenseGranted
from gomazon_webasyst.application.ports.installed_apps import InstalledAppMissing, InstalledAppResolved
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


TARGET = ApiMethodTarget(AppId("shop"), ApiMethodName("ping"))
PRINCIPAL = ApiPrincipalContext(42, ApiClientId("client"), ApiScope.of("shop"))


class Directory:
    def __init__(self, log, result):
        self.log, self.result = log, result
    async def resolve(self, app_id):
        self.log.append("app")
        return self.result


class Access:
    def __init__(self, log, result):
        self.log, self.result = log, result
    async def authorize(self, contact_id, app_id):
        self.log.append("access")
        return self.result


class License:
    def __init__(self, log, result):
        self.log, self.result = log, result
    async def check(self, app_id):
        self.log.append("license")
        return self.result


class FailAccess:
    async def authorize(self, contact_id, app_id):
        raise AssertionError("access must not be called")


class FailLicense:
    async def check(self, app_id):
        raise AssertionError("license must not be called")


@pytest.mark.asyncio
async def test_missing_app_stops_all_later_authorization_stages() -> None:
    log = []
    authorizer = ApiRequestAuthorizer(
        installed_apps=Directory(log, InstalledAppMissing(app_id=TARGET.app_id)),
        app_access=FailAccess(),
        license_policy=FailLicense(),
    )
    result = await authorizer.authorize(PRINCIPAL, TARGET)
    assert isinstance(result, ApiAuthorizationRejected)
    assert result.error.code is ApiFrameworkErrorCode.APP_NOT_INSTALLED
    assert log == ["app"]


@pytest.mark.asyncio
async def test_access_denial_stops_scope_and_license() -> None:
    log = []
    authorizer = ApiRequestAuthorizer(
        installed_apps=Directory(log, InstalledAppResolved(app_id=TARGET.app_id)),
        app_access=Access(log, ApiAppAccessDenied(contact_id=42, app_id=TARGET.app_id)),
        license_policy=FailLicense(),
    )
    result = await authorizer.authorize(PRINCIPAL, TARGET)
    assert isinstance(result, ApiAuthorizationRejected)
    assert result.error.code is ApiFrameworkErrorCode.ACCESS_DENIED
    assert log == ["app", "access"]


@pytest.mark.asyncio
async def test_scope_denial_stops_license() -> None:
    log = []
    principal = ApiPrincipalContext(42, ApiClientId("client"), ApiScope.of("site"))
    authorizer = ApiRequestAuthorizer(
        installed_apps=Directory(log, InstalledAppResolved(app_id=TARGET.app_id)),
        app_access=Access(log, ApiAppAccessGranted(contact_id=42, app_id=TARGET.app_id)),
        license_policy=FailLicense(),
    )
    result = await authorizer.authorize(principal, TARGET)
    assert isinstance(result, ApiAuthorizationRejected)
    assert result.error.code is ApiFrameworkErrorCode.ACCESS_DENIED
    assert log == ["app", "access"]


@pytest.mark.asyncio
async def test_license_block_maps_payment_required_after_scope() -> None:
    log = []
    authorizer = ApiRequestAuthorizer(
        installed_apps=Directory(log, InstalledAppResolved(app_id=TARGET.app_id)),
        app_access=Access(log, ApiAppAccessGranted(contact_id=42, app_id=TARGET.app_id)),
        license_policy=License(log, AppLicenseBlocked(app_id=TARGET.app_id)),
    )
    result = await authorizer.authorize(PRINCIPAL, TARGET)
    assert isinstance(result, ApiAuthorizationRejected)
    assert result.error.code is ApiFrameworkErrorCode.PAYMENT_REQUIRED
    assert result.error.http_status == 402
    assert log == ["app", "access", "license"]


@pytest.mark.asyncio
async def test_all_authorization_stages_grant() -> None:
    log = []
    authorizer = ApiRequestAuthorizer(
        installed_apps=Directory(log, InstalledAppResolved(app_id=TARGET.app_id)),
        app_access=Access(log, ApiAppAccessGranted(contact_id=42, app_id=TARGET.app_id)),
        license_policy=License(log, AppLicenseGranted(app_id=TARGET.app_id)),
    )
    result = await authorizer.authorize(PRINCIPAL, TARGET)
    assert isinstance(result, ApiAuthorizationGranted)
    assert log == ["app", "access", "license"]
