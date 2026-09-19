from pathlib import Path

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.composites.authorization import (
    ApiAuthorizationGranted,
    ApiAuthorizationRejected,
)
from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiPrincipalContext,
)
from gomazon_webasyst.application.api_execution.services.authorizer import (
    ApiRequestAuthorizer,
)
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiMethodName,
    ApiMethodTarget,
)
from gomazon_webasyst.application.ports.api_app_access import ApiAppAccessGranted
from gomazon_webasyst.application.ports.app_license import AppLicenseGranted
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolved,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.installer_policy import (
    NeverForceInstaller,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.consent_application_projector import (
    LegacyOAuthConsentApplicationProjector,
)
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode
from gomazon_webasyst.infrastructure.application_registry.filesystem_catalog import (
    FilesystemInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.oauth_authorization.app_catalog import (
    InstalledApplicationOAuthConsentAppCatalog,
)


class AllowAppAccess:
    async def authorize(self, contact_id: int, app_id: AppId):
        return ApiAppAccessGranted(contact_id=contact_id, app_id=app_id)


class AllowLicense:
    async def check(self, app_id: AppId):
        return AppLicenseGranted(app_id=app_id)


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _legacy_root(tmp_path: Path) -> Path:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-config/apps.php",
        "<?php return ['site' => true, 'disabled' => false];",
    )
    _write(
        root,
        "wa-apps/site/lib/config/app.php",
        "<?php return ['name' => 'Site', 'version' => '3.5.3', "
        "'vendor' => 'webasyst', 'icon' => 'img/site.svg'];",
    )
    _write(
        root,
        "wa-system/webasyst/lib/config/app.php",
        "<?php return ['name' => 'Webasyst', 'version' => '4.2.0', "
        "'vendor' => 'webasyst', 'header_items' => ['settings' => "
        "['name' => 'Settings', 'icon' => 'img/wa-settings/settings.svg']]];",
    )
    return root


@pytest.mark.asyncio
async def test_one_discovered_catalog_drives_api_existence_and_oauth_metadata(
    tmp_path: Path,
) -> None:
    catalog = FilesystemInstalledApplicationCatalog(
        _legacy_root(tmp_path),
        installer_policy=NeverForceInstaller(),
    )
    api_authorizer = ApiRequestAuthorizer(
        installed_apps=catalog,
        app_access=AllowAppAccess(),
        license_policy=AllowLicense(),
    )
    oauth_catalog = InstalledApplicationOAuthConsentAppCatalog(
        catalog,
        LegacyOAuthConsentApplicationProjector(),
    )
    principal = ApiPrincipalContext(
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("site"),
    )

    api_result = await api_authorizer.authorize(
        principal,
        ApiMethodTarget(AppId("site"), ApiMethodName("ping")),
    )
    oauth_result = await oauth_catalog.resolve(AppId("site"))

    assert isinstance(api_result, ApiAuthorizationGranted)
    assert isinstance(oauth_result, OAuthConsentApplicationResolved)
    assert oauth_result.application.display_name.value == "Site"
    assert oauth_result.application.icon.value == "wa-apps/site/img/site.svg"


@pytest.mark.asyncio
async def test_missing_or_disabled_app_is_missing_to_both_api_and_oauth(
    tmp_path: Path,
) -> None:
    catalog = FilesystemInstalledApplicationCatalog(
        _legacy_root(tmp_path),
        installer_policy=NeverForceInstaller(),
    )
    api_authorizer = ApiRequestAuthorizer(
        installed_apps=catalog,
        app_access=AllowAppAccess(),
        license_policy=AllowLicense(),
    )
    oauth_catalog = InstalledApplicationOAuthConsentAppCatalog(
        catalog,
        LegacyOAuthConsentApplicationProjector(),
    )
    principal = ApiPrincipalContext(
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("disabled"),
    )

    api_result = await api_authorizer.authorize(
        principal,
        ApiMethodTarget(AppId("disabled"), ApiMethodName("ping")),
    )
    oauth_result = await oauth_catalog.resolve(AppId("disabled"))

    assert isinstance(api_result, ApiAuthorizationRejected)
    assert api_result.error.code is ApiFrameworkErrorCode.APP_NOT_INSTALLED
    assert isinstance(oauth_result, OAuthConsentApplicationMissing)
