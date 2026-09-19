from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.entities.installed_plugin import InstalledPlugin
from gomazon_webasyst.application.plugins.vo.capabilities import (
    PluginCapabilities,
    PluginCapabilityName,
)
from gomazon_webasyst.application.plugins.vo.handlers import (
    PluginHandlerDeclaration,
    PluginHandlerDeclarations,
    PluginHandlerEventPattern,
    PluginHandlerMethodName,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.plugins.vo.metadata import (
    PluginDisplayName,
    PluginImageMissing,
    PluginImagePresent,
    PluginImageReference,
    PluginVendor,
    PluginVersion,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyApplicationConfigError,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.normalizer import (
    php_truthy,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayStringKey,
    PhpNull,
    PhpValue,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.raw_config import (
    php_string_mapping,
)
from gomazon_webasyst.compatibility.webasyst.plugins.raw_config import (
    php_array_values,
    php_method_names,
    php_string_keyed_entries,
)


_LEGACY_UNKNOWN_VENDOR = "local"
_LEGACY_DEFAULT_VERSION = "0.0.1"


def normalize_configured_plugin_ids(
    config: PhpValue,
    *,
    app_id: AppId,
) -> tuple[PluginId, ...]:
    mapping = php_string_mapping(
        config,
        context=f"wa-config/apps/{app_id.value}/plugins.php",
    )
    result: list[PluginId] = []
    for raw_plugin_id, enabled in mapping.items():
        if not php_truthy(enabled):
            continue
        try:
            result.append(PluginId(raw_plugin_id))
        except ValueError as error:
            raise LegacyApplicationConfigError(
                f"invalid configured plugin id: {raw_plugin_id!r}"
            ) from error
    return tuple(result)


def normalize_plugin_manifest(
    key: PluginKey,
    config: PhpValue,
) -> InstalledPlugin:
    mapping = php_string_mapping(
        config,
        context=f"{key.app_id.value}.{key.plugin_id.value} plugin manifest",
    )
    display_name = _required_string(mapping, "name", key)
    vendor = _optional_string(
        mapping,
        "vendor",
        default=_LEGACY_UNKNOWN_VENDOR,
        key=key,
    )
    version = _optional_string(
        mapping,
        "version",
        default=_LEGACY_DEFAULT_VERSION,
        key=key,
    )
    image = _normalize_image(mapping, key)
    capabilities = PluginCapabilities(
        frozenset(
            PluginCapabilityName(name)
            for name, value in mapping.items()
            if isinstance(value, bool) and value
        )
    )
    declarations = _normalize_handlers(mapping, key)
    return InstalledPlugin(
        key=key,
        display_name=PluginDisplayName(display_name),
        version=PluginVersion(version),
        vendor=PluginVendor(vendor),
        image=image,
        capabilities=capabilities,
        handler_declarations=declarations,
    )


def _required_string(
    mapping: dict[str, PhpValue],
    name: str,
    key: PluginKey,
) -> str:
    if name not in mapping:
        raise LegacyApplicationConfigError(
            f"{key.app_id.value}.{key.plugin_id.value} manifest is missing {name!r}"
        )
    value = mapping[name]
    if not isinstance(value, str) or not value:
        raise LegacyApplicationConfigError(
            f"{key.app_id.value}.{key.plugin_id.value} manifest {name!r} "
            "must be a non-empty string"
        )
    return value


def _optional_string(
    mapping: dict[str, PhpValue],
    name: str,
    *,
    default: str,
    key: PluginKey,
) -> str:
    if name not in mapping or isinstance(mapping[name], PhpNull):
        return default
    value = mapping[name]
    if not isinstance(value, str) or not value:
        raise LegacyApplicationConfigError(
            f"{key.app_id.value}.{key.plugin_id.value} manifest {name!r} "
            "must be a non-empty string"
        )
    return value


def _normalize_image(
    mapping: dict[str, PhpValue],
    key: PluginKey,
):
    if "img" not in mapping or isinstance(mapping["img"], PhpNull):
        return PluginImageMissing()
    value = mapping["img"]
    if not isinstance(value, str) or not value:
        raise LegacyApplicationConfigError(
            f"{key.app_id.value}.{key.plugin_id.value} manifest 'img' "
            "must be a non-empty string"
        )
    prefix = (
        f"wa-apps/{key.app_id.value}/plugins/{key.plugin_id.value}/"
    )
    return PluginImagePresent(
        PluginImageReference((prefix + value).lstrip("/"))
    )


def _normalize_handlers(
    mapping: dict[str, PhpValue],
    key: PluginKey,
) -> PluginHandlerDeclarations:
    raw_handlers: dict[str, PhpValue] = {}
    if "handlers" in mapping and not isinstance(mapping["handlers"], PhpNull):
        raw_handlers = dict(
            php_string_keyed_entries(
                mapping["handlers"],
                context=f"{key.app_id.value}.{key.plugin_id.value} handlers",
            )
        )

    if (
        "rights" in mapping
        and php_truthy(mapping["rights"])
        and "rights.config" not in raw_handlers
    ):
        raw_handlers["rights.config"] = "rightsConfig"
    if (
        "frontend" in mapping
        and php_truthy(mapping["frontend"])
        and "routing" not in raw_handlers
    ):
        raw_handlers["routing"] = "routing"
    if (
        "cron" in mapping
        and php_truthy(mapping["cron"])
        and "cron" not in raw_handlers
    ):
        raw_handlers["cron"] = "cron"

    declarations: list[PluginHandlerDeclaration] = []
    for event, handler in raw_handlers.items():
        if event == "*" and isinstance(handler, PhpArray):
            declarations.extend(_normalize_wildcard_handlers(handler, key))
            continue
        if not php_truthy(handler):
            continue
        methods = php_method_names(
            handler,
            context=f"{key.app_id.value}.{key.plugin_id.value} handler {event}",
        )
        declarations.append(
            PluginHandlerDeclaration(
                source_app_id=key.app_id,
                event_pattern=PluginHandlerEventPattern(event),
                methods=tuple(PluginHandlerMethodName(method) for method in methods),
            )
        )
    return PluginHandlerDeclarations(tuple(declarations))


def _normalize_wildcard_handlers(
    value: PhpArray,
    key: PluginKey,
) -> tuple[PluginHandlerDeclaration, ...]:
    declarations: list[PluginHandlerDeclaration] = []
    for index, item in enumerate(
        php_array_values(
            value,
            context=f"{key.app_id.value}.{key.plugin_id.value} wildcard handlers",
        )
    ):
        mapping = php_string_mapping(
            item,
            context=(
                f"{key.app_id.value}.{key.plugin_id.value} wildcard handler {index}"
            ),
        )
        if "event" not in mapping or not isinstance(mapping["event"], str):
            raise LegacyApplicationConfigError(
                f"wildcard handler {index} requires event"
            )
        event = mapping["event"]
        if not event:
            raise LegacyApplicationConfigError(
                f"wildcard handler {index} event must not be empty"
            )
        source_app_id = key.app_id
        if "event_app_id" in mapping:
            raw_source = mapping["event_app_id"]
            if not isinstance(raw_source, str) or not raw_source:
                raise LegacyApplicationConfigError(
                    f"wildcard handler {index} event_app_id must be a string"
                )
            try:
                source_app_id = AppId(raw_source)
            except ValueError as error:
                raise LegacyApplicationConfigError(
                    f"invalid wildcard event_app_id: {raw_source!r}"
                ) from error
        if "method" not in mapping:
            raise LegacyApplicationConfigError(
                f"wildcard handler {index} requires method"
            )
        methods = php_method_names(
            mapping["method"],
            context=f"wildcard handler {index}",
        )
        declarations.append(
            PluginHandlerDeclaration(
                source_app_id=source_app_id,
                event_pattern=PluginHandlerEventPattern(event),
                methods=tuple(PluginHandlerMethodName(method) for method in methods),
            )
        )
    return tuple(declarations)
