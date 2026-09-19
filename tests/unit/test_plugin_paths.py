from pathlib import Path

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.vo.identity import PluginId
from gomazon_webasyst.compatibility.webasyst.plugins.paths import (
    LegacyPluginIdRejected,
    LegacyPluginPathEscape,
    LegacyPluginPathPolicy,
)


def test_plugin_paths_are_derived_under_webasyst_root(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    policy = LegacyPluginPathPolicy(root)
    assert policy.plugins_config_path(AppId("site")) == (
        root.resolve() / "wa-config" / "apps" / "site" / "plugins.php"
    )
    assert policy.plugin_manifest_path(
        AppId("site"),
        PluginId("rublesign"),
    ) == (
        root.resolve()
        / "wa-apps"
        / "site"
        / "plugins"
        / "rublesign"
        / "lib"
        / "config"
        / "plugin.php"
    )


@pytest.mark.parametrize("plugin_id", ["../x", "bad/plugin", "Bad", "a\\b"])
def test_unsafe_plugin_ids_are_rejected(tmp_path: Path, plugin_id: str) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    policy = LegacyPluginPathPolicy(root)
    with pytest.raises(LegacyPluginIdRejected):
        policy.plugin_manifest_path(AppId("site"), PluginId(plugin_id))


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "wa-apps").mkdir()
    (root / "wa-apps" / "site").symlink_to(outside, target_is_directory=True)
    policy = LegacyPluginPathPolicy(root)
    with pytest.raises(LegacyPluginPathEscape):
        policy.plugin_manifest_path(AppId("site"), PluginId("demo"))
