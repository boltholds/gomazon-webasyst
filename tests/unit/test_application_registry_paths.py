from pathlib import Path

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.compatibility.webasyst.application_registry.paths import (
    LegacyApplicationIdRejected,
    LegacyApplicationPathEscape,
    LegacyApplicationPathPolicy,
)


def test_paths_resolve_apps_config_and_ordinary_manifest_under_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    policy = LegacyApplicationPathPolicy(root)

    assert policy.apps_config_path() == root.resolve() / "wa-config" / "apps.php"
    assert policy.app_manifest_path(AppId("site")) == (
        root.resolve() / "wa-apps" / "site" / "lib" / "config" / "app.php"
    )


def test_webasyst_manifest_uses_system_application_path(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    policy = LegacyApplicationPathPolicy(root)

    assert policy.app_manifest_path(AppId("webasyst")) == (
        root.resolve()
        / "wa-system"
        / "webasyst"
        / "lib"
        / "config"
        / "app.php"
    )


@pytest.mark.parametrize(
    "value",
    [
        "../shop",
        "shop/../../outside",
        r"shop\..\outside",
        "/absolute",
        ".",
        "..",
        "shop.app",
        "Shop",
        "shop\x00evil",
        "шоп",
        "-shop",
        "_shop",
    ],
)
def test_rejects_app_ids_that_are_not_safe_legacy_path_segments(
    tmp_path: Path,
    value: str,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    policy = LegacyApplicationPathPolicy(root)

    with pytest.raises(LegacyApplicationIdRejected):
        policy.app_manifest_path(AppId(value))


@pytest.mark.parametrize(
    "value",
    ["a", "shop", "api_explorer", "my-app", "app2"],
)
def test_accepts_lowercase_ascii_filesystem_safe_app_ids(
    tmp_path: Path,
    value: str,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    policy = LegacyApplicationPathPolicy(root)

    path = policy.app_manifest_path(AppId(value))

    assert path.is_relative_to(root.resolve())


def test_rejects_symlink_that_escapes_webasyst_root(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    outside = tmp_path / "outside"
    (root / "wa-apps").mkdir(parents=True)
    outside.mkdir()
    (root / "wa-apps" / "evil").symlink_to(outside, target_is_directory=True)
    policy = LegacyApplicationPathPolicy(root)

    with pytest.raises(LegacyApplicationPathEscape):
        policy.app_manifest_path(AppId("evil"))


def test_symlink_that_stays_inside_root_is_allowed(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    target = root / "real-app"
    (root / "wa-apps").mkdir(parents=True)
    target.mkdir()
    (root / "wa-apps" / "alias").symlink_to(target, target_is_directory=True)
    policy = LegacyApplicationPathPolicy(root)

    path = policy.app_manifest_path(AppId("alias"))

    assert path == target.resolve() / "lib" / "config" / "app.php"


def test_constructor_canonicalizes_root_and_requires_existing_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "webasyst"
    with pytest.raises(FileNotFoundError):
        LegacyApplicationPathPolicy(root)

    root.mkdir()
    policy = LegacyApplicationPathPolicy(root / ".")

    assert policy.root == root.resolve()



def test_backend_routing_path_uses_same_containment_policy(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    policy = LegacyApplicationPathPolicy(root)

    assert policy.backend_routing_path(AppId("team")) == (
        root
        / "wa-apps"
        / "team"
        / "lib"
        / "config"
        / "routing.backend.php"
    ).resolve()
