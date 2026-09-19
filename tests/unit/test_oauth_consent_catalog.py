from importlib import import_module

import pytest

from gomazon_webasyst.application.access_values import AppId


def _modules():
    try:
        entity = import_module(
            "gomazon_webasyst.application.oauth_authorization.entities.consent_application"
        )
        client = import_module(
            "gomazon_webasyst.application.oauth_authorization.vo.client"
        )
        ports = import_module(
            "gomazon_webasyst.application.ports.oauth_consent_apps"
        )
        infra = import_module(
            "gomazon_webasyst.infrastructure.oauth_authorization.app_catalog"
        )
        return entity, client, ports, infra
    except ModuleNotFoundError as error:
        pytest.fail(f"oauth consent catalog missing: {error}")


def app(app_id: str, name: str):
    entity, client, _, _ = _modules()
    return entity.OAuthConsentApplication(
        app_id=AppId(app_id),
        display_name=client.OAuthAppDisplayName(name),
        icon=client.OAuthAppIconReference(f"/{app_id}.png"),
    )


def test_catalog_resolves_registered_entity_and_reports_missing() -> None:
    _, _, ports, infra = _modules()
    shop = app("shop", "Shop")
    catalog = infra.InMemoryOAuthConsentAppCatalog((shop,))

    resolved = catalog.resolve(AppId("shop"))
    missing = catalog.resolve(AppId("crm"))

    assert isinstance(resolved, ports.OAuthConsentApplicationResolved)
    assert resolved.application is shop
    assert isinstance(missing, ports.OAuthConsentApplicationMissing)
    assert missing.app_id == AppId("crm")


def test_catalog_rejects_duplicate_app_identity() -> None:
    _, _, _, infra = _modules()
    first = app("shop", "Shop")
    second = app("shop", "Other Shop")

    with pytest.raises(ValueError, match="duplicate"):
        infra.InMemoryOAuthConsentAppCatalog((first, second))
