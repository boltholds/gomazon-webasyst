from types import SimpleNamespace

from gomazon_webasyst.application.api_execution.composites.pipeline import (
    ApiExecutionPipeline,
)
from gomazon_webasyst.application.application_registry import (
    StaticApplicationRegistry,
)
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


def test_default_api_execution_composition_uses_empty_explicit_registries() -> None:
    components = create_default_api_execution_components(
        session_factory=object(),
        resolve_api_access_token=object(),
        api_enabled=True,
        disable_message="",
        force_https=False,
    )

    assert isinstance(components.pipeline, ApiExecutionPipeline)
    assert isinstance(
        components.method_registry,
        InMemoryApiMethodRegistry,
    )
    assert isinstance(
        components.application_registry,
        StaticApplicationRegistry,
    )
    assert components.application_registry.list_catalog_apps() == ()


def test_custom_composition_preserves_registry_and_policy_identity() -> None:
    method_registry = SimpleNamespace(resolve=lambda target: None)
    application_registry = SimpleNamespace(resolve_app=lambda app_id: None)
    license_policy = AllowAllAppLicensePolicy()

    components = create_api_execution_components(
        session_factory=object(),
        resolve_api_access_token=object(),
        method_registry=method_registry,
        application_registry=application_registry,
        license_policy=license_policy,
        api_enabled=True,
        disable_message="",
        force_https=False,
    )

    assert components.method_registry is method_registry
    assert components.application_registry is application_registry
