from pathlib import Path

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilityName,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyApplicationConfigError,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.normalizer import (
    normalize_application_manifest,
    normalize_configured_app_ids,
    php_truthy,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayAutoKey,
    PhpArrayEntry,
    PhpArrayStringKey,
    PhpNull,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "webasyst_4_2" / "application_registry"


def _fixture(name: str):
    return parse_php_return_value((FIXTURES / name).read_text(encoding="utf-8"))


def _icons(application) -> dict[int, str]:
    return {
        item.size: item.reference.value
        for item in application.icons.items
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (False, False),
        (True, True),
        (0, False),
        (1, True),
        (0.0, False),
        (0.5, True),
        ("", False),
        ("0", False),
        ("00", True),
        ("false", True),
        (PhpNull(), False),
        (PhpArray(()), False),
        (
            PhpArray(
                (
                    PhpArrayEntry(
                        key=PhpArrayAutoKey(),
                        value="x",
                    ),
                )
            ),
            True,
        ),
    ],
)
def test_php_truthy_matches_characterized_php_scalar_and_array_semantics(
    value,
    expected: bool,
) -> None:
    assert php_truthy(value) is expected


def test_configured_app_ids_preserve_order_and_drop_falsey_entries() -> None:
    apps = normalize_configured_app_ids(_fixture("apps_enabled_disabled.php"))

    assert apps == (
        AppId("site"),
        AppId("developer"),
        AppId("team"),
    )


def test_configured_app_duplicate_key_uses_php_last_value_without_reordering() -> None:
    config = parse_php_return_value(
        "<?php return ['site' => false, 'blog' => true, 'site' => true];"
    )

    assert normalize_configured_app_ids(config) == (
        AppId("site"),
        AppId("blog"),
    )


def test_configured_app_ids_require_string_keys_and_top_level_array() -> None:
    with pytest.raises(LegacyApplicationConfigError):
        normalize_configured_app_ids("not-an-array")

    with pytest.raises(LegacyApplicationConfigError):
        normalize_configured_app_ids(
            PhpArray((PhpArrayEntry(PhpArrayAutoKey(), True),))
        )


def test_scalar_icon_is_prefixed_and_fills_48_24_16() -> None:
    app = normalize_application_manifest(
        AppId("site"),
        _fixture("app_scalar_icon.php"),
    )

    assert app.display_name.value == "Site"
    assert app.vendor.value == "webasyst"
    assert app.version.value == "3.5.3"
    assert _icons(app) == {
        16: "wa-apps/site/img/site.svg",
        24: "wa-apps/site/img/site.svg",
        48: "wa-apps/site/img/site.svg",
    }


def test_img_fallback_fills_48_24_16_and_false_capability_is_omitted() -> None:
    app = normalize_application_manifest(
        AppId("developer"),
        _fixture("app_img_fallback.php"),
    )

    assert _icons(app) == {
        16: "wa-apps/developer/img/developer.png",
        24: "wa-apps/developer/img/developer.png",
        48: "wa-apps/developer/img/developer.png",
    }
    assert ApplicationCapabilityName("frontend") not in app.capabilities.values
    assert ApplicationCapabilityName("csrf") in app.capabilities.values
    assert ApplicationCapabilityName("plugins") in app.capabilities.values


def test_icon_map_is_prefixed_and_preserves_explicit_sizes_with_img_fallback() -> None:
    app = normalize_application_manifest(
        AppId("custom"),
        _fixture("app_icon_map.php"),
    )

    assert _icons(app) == {
        16: "wa-apps/custom/img/icon16.png",
        24: "wa-apps/custom/img/icon48.png",
        48: "wa-apps/custom/img/icon48.png",
    }


def test_webasyst_header_settings_icon_uses_wa_content_prefix() -> None:
    app = normalize_application_manifest(
        AppId("webasyst"),
        _fixture("webasyst_app.php"),
    )

    settings = next(
        item
        for item in app.header_items.items
        if item.item_id.value == "settings"
    )
    assert _icons(
        type("_HeaderApp", (), {"icons": settings.icons})()
    ) == {
        48: "wa-content/img/wa-settings/settings.svg"
    }


def test_true_boolean_manifest_fields_become_open_capabilities() -> None:
    app = normalize_application_manifest(
        AppId("site"),
        _fixture("app_scalar_icon.php"),
    )

    assert {
        capability.value for capability in app.capabilities.values
    } >= {"frontend", "rights", "plugins", "csrf"}


def test_missing_vendor_and_version_use_legacy_defaults() -> None:
    manifest = parse_php_return_value(
        "<?php return ['name' => 'Local App'];"
    )

    app = normalize_application_manifest(AppId("localapp"), manifest)

    assert app.vendor.value == "local"
    assert app.version.value == "0.0.1"


@pytest.mark.parametrize(
    "source",
    [
        "<?php return [];",
        "<?php return ['name' => ''];",
        "<?php return ['name' => false];",
        "<?php return 'not-an-array';",
    ],
)
def test_invalid_manifest_name_or_shape_fails_deterministically(
    source: str,
) -> None:
    with pytest.raises(LegacyApplicationConfigError):
        normalize_application_manifest(
            AppId("broken"),
            parse_php_return_value(source),
        )
