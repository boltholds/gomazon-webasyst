from types import SimpleNamespace

from gomazon_webasyst.application.api_execution.composites.pipeline import ApiExecutionPipeline
from gomazon_webasyst.compatibility.webasyst.api.services.license import (
    AllowAllAppLicensePolicy,
)
from gomazon_webasyst.composition.api_execution import (
    create_api_execution_components,
    create_default_api_execution_components,
)
from gomazon_webasyst.infrastructure.api_execution.method_registry import (
    InMemoryApiMethodRegistry,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)


def test_default_api_execution_composition_uses_explicit_catalog_and_empty_method_registry() -> None:
    catalog = InMemoryInstalledApplicationCatalog(())
    components = create_default_api_execution_components(
        session_factory=object(),
        resolve_api_access_token=object(),
        installed_application_catalog=catalog,
        api_enabled=True,
        disable_message="",
        force_https=False,
    )
    assert isinstance(components.pipeline, ApiExecutionPipeline)
    assert isinstance(components.method_registry, InMemoryApiMethodRegistry)
    assert components.installed_application_catalog is catalog


def test_custom_composition_preserves_registry_catalog_and_policy_identity() -> None:
    registry = SimpleNamespace(resolve=lambda target: None)
    catalog = InMemoryInstalledApplicationCatalog(())
    license_policy = AllowAllAppLicensePolicy()
    components = create_api_execution_components(
        session_factory=object(),
        resolve_api_access_token=object(),
        method_registry=registry,
        installed_application_catalog=catalog,
        license_policy=license_policy,
        api_enabled=True,
        disable_message="",
        force_https=False,
    )
    assert components.method_registry is registry
    assert components.installed_application_catalog is catalog
