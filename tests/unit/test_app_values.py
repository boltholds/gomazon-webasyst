import pytest

from gomazon_webasyst.application import access_values
from gomazon_webasyst.application.app_values import AppId, PluginId, PluginRef


def test_app_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        AppId("")


def test_app_id_preserves_existing_length_limit() -> None:
    with pytest.raises(ValueError, match="must not exceed 32"):
        AppId("a" * 33)


def test_plugin_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        PluginId("")


def test_plugin_ref_has_value_semantics() -> None:
    assert PluginRef(AppId("blog"), PluginId("markdown")) == PluginRef(
        AppId("blog"),
        PluginId("markdown"),
    )


def test_access_values_reexports_the_shared_app_id_type() -> None:
    assert access_values.AppId is AppId
