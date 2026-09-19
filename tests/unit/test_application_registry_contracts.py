import pytest
from pydantic import ValidationError

from gomazon_webasyst.application.app_values import AppId, PluginId, PluginRef
from gomazon_webasyst.application.ports.application_registry import (
    ApplicationDisabled,
    ApplicationEnabled,
    ApplicationUnknown,
    PluginDisabled,
    PluginEnabled,
    PluginListOwnerDisabled,
    PluginListOwnerUnknown,
    PluginListResolved,
    PluginOwnerDisabled,
    PluginUnknown,
)
from gomazon_webasyst.contracts.applications import (
    ApplicationCapabilities,
    ApplicationDescriptor,
    ExternalCalendarIntegration,
    PluginDescriptor,
    RequiresPermissionHeaderAccess,
)
from gomazon_webasyst.contracts.enums import (
    ApplicationResolutionKind,
    ExternalCalendarIntegrationLevel,
    PluginListResultKind,
    PluginResolutionKind,
)


def test_application_descriptor_serializes_shared_app_id() -> None:
    descriptor = ApplicationDescriptor(
        id=AppId("blog"),
        name="Blog",
        capabilities=ApplicationCapabilities(frontend=True, plugins=True),
    )

    payload = descriptor.model_dump()

    assert payload["id"] == {"value": "blog"}
    assert payload["capabilities"]["frontend"] is True
    assert payload["capabilities"]["plugins"] is True
    assert payload["capabilities"]["system"] is False
    assert payload["framework_system"] is False


def test_application_descriptor_forbids_opaque_extra_metadata() -> None:
    with pytest.raises(ValidationError):
        ApplicationDescriptor(
            id=AppId("blog"),
            name="Blog",
            metadata={"legacy": "bag"},
        )


def test_header_access_is_structural() -> None:
    access = RequiresPermissionHeaderAccess(name="backend")

    assert access.kind.value == "requires_permission"
    assert access.name == "backend"


def test_external_calendar_integration_is_structural() -> None:
    descriptor = PluginDescriptor.model_validate(
        {
            "ref": {
                "app_id": {"value": "team"},
                "plugin_id": {"value": "ics"},
            },
            "name": "ICS",
            "integration": {
                "kind": "external_calendar",
                "level": "subscription",
            },
        }
    )

    assert isinstance(descriptor.integration, ExternalCalendarIntegration)
    assert (
        descriptor.integration.level
        is ExternalCalendarIntegrationLevel.SUBSCRIPTION
    )


def test_application_resolution_variants_are_explicit() -> None:
    descriptor = ApplicationDescriptor(id=AppId("blog"), name="Blog")

    assert ApplicationEnabled(descriptor).kind is ApplicationResolutionKind.ENABLED
    assert ApplicationDisabled(descriptor).kind is ApplicationResolutionKind.DISABLED
    assert ApplicationUnknown(AppId("missing")).kind is ApplicationResolutionKind.UNKNOWN


def test_plugin_resolution_variants_are_explicit() -> None:
    owner = ApplicationDescriptor(id=AppId("blog"), name="Blog")
    plugin = PluginDescriptor(
        ref=PluginRef(AppId("blog"), PluginId("markdown")),
        name="Markdown",
    )

    assert PluginEnabled(plugin).kind is PluginResolutionKind.ENABLED
    assert PluginDisabled(plugin).kind is PluginResolutionKind.DISABLED
    assert (
        PluginOwnerDisabled(plugin, owner).kind
        is PluginResolutionKind.OWNER_DISABLED
    )
    assert (
        PluginUnknown(PluginRef(AppId("blog"), PluginId("missing"))).kind
        is PluginResolutionKind.UNKNOWN
    )


def test_plugin_list_results_do_not_use_empty_tuple_as_state() -> None:
    app_id = AppId("blog")

    assert PluginListResolved(app_id, ()).kind is PluginListResultKind.LISTED
    assert (
        PluginListOwnerDisabled(app_id).kind
        is PluginListResultKind.OWNER_DISABLED
    )
    assert (
        PluginListOwnerUnknown(app_id).kind
        is PluginListResultKind.OWNER_UNKNOWN
    )
