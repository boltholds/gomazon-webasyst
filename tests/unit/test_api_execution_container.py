from types import SimpleNamespace

from gomazon_webasyst.application.api_execution.composites.pipeline import ApiExecutionPipeline
from gomazon_webasyst.compatibility.webasyst.api.services.license import AllowAllAppLicensePolicy
from gomazon_webasyst.composition.api_execution import (
    create_api_execution_components,
    create_default_api_execution_components,
)
from gomazon_webasyst.infrastructure.api_execution.app_directory import InMemoryInstalledAppDirectory
from gomazon_webasyst.infrastructure.api_execution.method_registry import InMemoryApiMethodRegistry


def test_default_api_execution_composition_uses_empty_explicit_registries() -> None:
    components = create_default_api_execution_components(
        session_factory=object(),
        resolve_api_access_token=object(),
        api_enabled=True,
        disable_message="",
        force_https=False,
    )
    assert isinstance(components.pipeline, ApiExecutionPipeline)
    assert isinstance(components.method_registry, InMemoryApiMethodRegistry)
    assert isinstance(components.installed_app_directory, InMemoryInstalledAppDirectory)


def test_custom_composition_preserves_registry_directory_and_policy_identity() -> None:
    registry = SimpleNamespace(resolve=lambda target: None)
    directory = SimpleNamespace(resolve=lambda app_id: None)
    license_policy = AllowAllAppLicensePolicy()
    components = create_api_execution_components(
        session_factory=object(),
        resolve_api_access_token=object(),
        method_registry=registry,
        installed_app_directory=directory,
        license_policy=license_policy,
        api_enabled=True,
        disable_message="",
        force_https=False,
    )
    assert components.method_registry is registry
    assert components.installed_app_directory is directory
