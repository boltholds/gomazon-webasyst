from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilities,
    ApplicationCapabilityName,
)
from gomazon_webasyst.application.application_registry.vo.header_items import (
    ApplicationHeaderItem,
    ApplicationHeaderItemId,
    ApplicationHeaderItems,
)
from gomazon_webasyst.application.application_registry.vo.icons import (
    ApplicationIcon,
    ApplicationIconReference,
    ApplicationIconSet,
)
from gomazon_webasyst.application.application_registry.vo.metadata import (
    ApplicationDisplayName,
    ApplicationVendor,
    ApplicationVersion,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyApplicationConfigError,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayIntKey,
    PhpArrayStringKey,
    PhpNull,
    PhpValue,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.raw_config import (
    php_string_mapping,
)


_LEGACY_UNKNOWN_VENDOR = "local"
_LEGACY_DEFAULT_VERSION = "0.0.1"


def php_truthy(value: PhpValue) -> bool:
    if isinstance(value, PhpNull):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value not in {"", "0"}
    if isinstance(value, PhpArray):
        return bool(value.entries)
    raise TypeError(f"unsupported PHP value: {type(value)!r}")


def normalize_configured_app_ids(config: PhpValue) -> tuple[AppId, ...]:
    mapping = php_string_mapping(config, context="wa-config/apps.php")
    result: list[AppId] = []
    for raw_app_id, enabled in mapping.items():
        if not php_truthy(enabled):
            continue
        try:
            result.append(AppId(raw_app_id))
        except ValueError as error:
            raise LegacyApplicationConfigError(
                f"invalid configured application id: {raw_app_id!r}"
            ) from error
    return tuple(result)


def normalize_application_manifest(
    app_id: AppId,
    config: PhpValue,
) -> InstalledApplication:
    mapping = php_string_mapping(
        config,
        context=f"{app_id.value} application manifest",
    )

    display_name = _required_string(mapping, "name", app_id)
    vendor = _optional_string(
        mapping,
        "vendor",
        default=_LEGACY_UNKNOWN_VENDOR,
        app_id=app_id,
    )
    version = _optional_string(
        mapping,
        "version",
        default=_LEGACY_DEFAULT_VERSION,
        app_id=app_id,
    )

    app_prefix = (
        "wa-system/webasyst/"
        if app_id.value == "webasyst"
        else f"wa-apps/{app_id.value}/"
    )
    icons = _normalize_app_icons(mapping, app_prefix, app_id)
    capabilities = ApplicationCapabilities(
        frozenset(
            ApplicationCapabilityName(key)
            for key, value in mapping.items()
            if isinstance(value, bool) and value
        )
    )
    header_items = _normalize_header_items(
        mapping,
        app_id=app_id,
        ordinary_prefix=app_prefix,
    )

    return InstalledApplication(
        app_id=app_id,
        display_name=ApplicationDisplayName(display_name),
        icons=icons,
        vendor=ApplicationVendor(vendor),
        version=ApplicationVersion(version),
        capabilities=capabilities,
        header_items=header_items,
    )


def _required_string(
    mapping: dict[str, PhpValue],
    key: str,
    app_id: AppId,
) -> str:
    if key not in mapping:
        raise LegacyApplicationConfigError(
            f"{app_id.value} manifest is missing required {key!r}"
        )
    value = mapping[key]
    if not isinstance(value, str) or not value:
        raise LegacyApplicationConfigError(
            f"{app_id.value} manifest {key!r} must be a non-empty string"
        )
    return value


def _optional_string(
    mapping: dict[str, PhpValue],
    key: str,
    *,
    default: str,
    app_id: AppId,
) -> str:
    if key not in mapping or isinstance(mapping[key], PhpNull):
        return default
    value = mapping[key]
    if not isinstance(value, str) or not value:
        raise LegacyApplicationConfigError(
            f"{app_id.value} manifest {key!r} must be a non-empty string"
        )
    return value


def _normalize_app_icons(
    mapping: dict[str, PhpValue],
    prefix: str,
    app_id: AppId,
) -> ApplicationIconSet:
    icons = _read_icon_value(mapping, prefix=prefix, app_id=app_id)

    img_reference = ""
    if "img" in mapping and not isinstance(mapping["img"], PhpNull):
        raw_img = mapping["img"]
        if not isinstance(raw_img, str) or not raw_img:
            raise LegacyApplicationConfigError(
                f"{app_id.value} manifest 'img' must be a non-empty string"
            )
        img_reference = _prefix_reference(prefix, raw_img)
    elif 48 in icons:
        img_reference = icons[48]

    if img_reference:
        icons.setdefault(48, img_reference)
        icons.setdefault(24, icons[48])
        icons.setdefault(16, icons[24])

    return _icon_set(icons)


def _read_icon_value(
    mapping: dict[str, PhpValue],
    *,
    prefix: str,
    app_id: AppId,
) -> dict[int, str]:
    if "icon" not in mapping or isinstance(mapping["icon"], PhpNull):
        return {}

    raw_icon = mapping["icon"]
    if isinstance(raw_icon, str):
        if not raw_icon:
            raise LegacyApplicationConfigError(
                f"{app_id.value} manifest 'icon' must not be empty"
            )
        return {48: _prefix_reference(prefix, raw_icon)}

    if not isinstance(raw_icon, PhpArray):
        raise LegacyApplicationConfigError(
            f"{app_id.value} manifest 'icon' must be a string or PHP array"
        )

    icons: dict[int, str] = {}
    for entry in raw_icon.entries:
        if isinstance(entry.key, PhpArrayIntKey):
            size = entry.key.value
        elif isinstance(entry.key, PhpArrayStringKey) and entry.key.value.isdigit():
            size = int(entry.key.value)
        else:
            raise LegacyApplicationConfigError(
                f"{app_id.value} icon map requires integer sizes"
            )
        if size <= 0:
            raise LegacyApplicationConfigError(
                f"{app_id.value} icon size must be positive"
            )
        if not isinstance(entry.value, str) or not entry.value:
            raise LegacyApplicationConfigError(
                f"{app_id.value} icon reference must be a non-empty string"
            )
        icons[size] = _prefix_reference(prefix, entry.value)
    return icons


def _normalize_header_items(
    mapping: dict[str, PhpValue],
    *,
    app_id: AppId,
    ordinary_prefix: str,
) -> ApplicationHeaderItems:
    if "header_items" not in mapping or isinstance(mapping["header_items"], PhpNull):
        return ApplicationHeaderItems(())

    raw_items = mapping["header_items"]
    if not isinstance(raw_items, PhpArray):
        raise LegacyApplicationConfigError(
            f"{app_id.value} manifest 'header_items' must be a PHP array"
        )

    prefix = "wa-content/" if app_id.value == "webasyst" else ordinary_prefix
    items: list[ApplicationHeaderItem] = []
    seen: set[str] = set()

    for entry in raw_items.entries:
        if not isinstance(entry.key, PhpArrayStringKey):
            raise LegacyApplicationConfigError(
                f"{app_id.value} header item ids must be strings"
            )
        if entry.key.value in seen:
            raise LegacyApplicationConfigError(
                f"duplicate header item id: {entry.key.value}"
            )
        seen.add(entry.key.value)

        item_mapping = php_string_mapping(
            entry.value,
            context=f"{app_id.value} header item {entry.key.value}",
        )
        if "name" not in item_mapping:
            continue
        raw_name = item_mapping["name"]
        if not isinstance(raw_name, str) or not raw_name:
            continue

        header_icons = _read_header_icons(
            item_mapping,
            prefix=prefix,
            app_id=app_id,
        )
        items.append(
            ApplicationHeaderItem(
                item_id=ApplicationHeaderItemId(entry.key.value),
                display_name=ApplicationDisplayName(raw_name),
                icons=_icon_set(header_icons),
            )
        )

    return ApplicationHeaderItems(tuple(items))


def _read_header_icons(
    mapping: dict[str, PhpValue],
    *,
    prefix: str,
    app_id: AppId,
) -> dict[int, str]:
    icons = _read_icon_value(mapping, prefix=prefix, app_id=app_id)
    if icons:
        return icons

    if "img" in mapping and not isinstance(mapping["img"], PhpNull):
        raw_img = mapping["img"]
        if not isinstance(raw_img, str) or not raw_img:
            raise LegacyApplicationConfigError(
                f"{app_id.value} header item 'img' must be a non-empty string"
            )
        return {48: _prefix_reference(prefix, raw_img)}
    return {}


def _prefix_reference(prefix: str, reference: str) -> str:
    return (prefix + reference).lstrip("/")


def _icon_set(icons: dict[int, str]) -> ApplicationIconSet:
    return ApplicationIconSet(
        tuple(
            ApplicationIcon(
                size=size,
                reference=ApplicationIconReference(reference),
            )
            for size, reference in sorted(icons.items())
        )
    )
