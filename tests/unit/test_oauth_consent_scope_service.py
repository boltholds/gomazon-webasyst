import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRequestedScope,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
)
from gomazon_webasyst.application.ports.oauth_consent_access import (
    OAuthConsentAccessDenied,
    OAuthConsentAccessGranted,
)
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolved,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject


SUBJECT = AuthenticatedSubject(id=42, login="admin")
SHOP = OAuthConsentApplication(
    app_id=AppId("shop"),
    display_name=OAuthAppDisplayName("Shop"),
    icon=OAuthAppIconReference("/shop.png"),
)
CRM = OAuthConsentApplication(
    app_id=AppId("crm"),
    display_name=OAuthAppDisplayName("CRM"),
    icon=OAuthAppIconReference("/crm.png"),
)
TASKS = OAuthConsentApplication(
    app_id=AppId("tasks"),
    display_name=OAuthAppDisplayName("Tasks"),
    icon=OAuthAppIconReference("/tasks.png"),
)


def _service_class():
    try:
        from gomazon_webasyst.application.oauth_authorization.services.scope import (
            OAuthConsentScopeService,
        )
        return OAuthConsentScopeService
    except ModuleNotFoundError as error:
        pytest.fail(f"oauth consent scope service missing: {error}")


class Catalog:
    def __init__(self, applications):
        self.applications = {
            application.app_id: application for application in applications
        }
        self.calls = []

    async def resolve(self, app_id):
        self.calls.append(app_id)
        if app_id not in self.applications:
            return OAuthConsentApplicationMissing(app_id)
        return OAuthConsentApplicationResolved(self.applications[app_id])


class AccessPolicy:
    def __init__(self, granted):
        self.granted = set(granted)
        self.calls = []

    async def authorize(self, subject, app_id):
        self.calls.append((subject, app_id))
        if app_id in self.granted:
            return OAuthConsentAccessGranted(app_id)
        return OAuthConsentAccessDenied(app_id)


@pytest.mark.asyncio
async def test_scope_filter_preserves_survivor_order_and_hides_denied_apps() -> None:
    catalog = Catalog((SHOP, CRM, TASKS))
    access = AccessPolicy({AppId("shop"), AppId("tasks")})
    service = _service_class()(catalog=catalog, access=access)

    result = await service.filter(
        SUBJECT,
        OAuthRequestedScope(
            (
                AppId("shop"),
                AppId("missing"),
                AppId("crm"),
                AppId("shop"),
                AppId("tasks"),
            )
        ),
    )

    assert result.scope.apps == (AppId("shop"), AppId("tasks"))
    assert result.applications == (SHOP, TASKS)
    assert catalog.calls == (
        [AppId("shop"), AppId("missing"), AppId("crm"), AppId("tasks")]
    )
    assert access.calls == [
        (SUBJECT, AppId("shop")),
        (SUBJECT, AppId("crm")),
        (SUBJECT, AppId("tasks")),
    ]


@pytest.mark.asyncio
async def test_missing_catalog_entries_are_never_sent_to_access_policy() -> None:
    catalog = Catalog((SHOP,))
    access = AccessPolicy({AppId("shop")})
    service = _service_class()(catalog=catalog, access=access)

    await service.filter(
        SUBJECT,
        OAuthRequestedScope((AppId("missing"), AppId("shop"))),
    )

    assert access.calls == [(SUBJECT, AppId("shop"))]


@pytest.mark.asyncio
async def test_empty_effective_scope_is_explicit_without_constructing_empty_api_scope() -> None:
    catalog = Catalog((CRM,))
    access = AccessPolicy(set())
    service = _service_class()(catalog=catalog, access=access)

    result = await service.filter(
        SUBJECT,
        OAuthRequestedScope((AppId("missing"), AppId("crm"))),
    )

    module = __import__(
        "gomazon_webasyst.application.oauth_authorization.services.scope",
        fromlist=["OAuthEffectiveScopeEmpty"],
    )
    assert isinstance(result, module.OAuthEffectiveScopeEmpty)
