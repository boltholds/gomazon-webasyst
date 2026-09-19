from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyApplicationConfigError,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayStringKey,
    PhpValue,
)


def php_string_mapping(
    value: PhpValue,
    *,
    context: str,
) -> dict[str, PhpValue]:
    if not isinstance(value, PhpArray):
        raise LegacyApplicationConfigError(f"{context} must be a PHP array")

    result: dict[str, PhpValue] = {}
    for entry in value.entries:
        if not isinstance(entry.key, PhpArrayStringKey):
            raise LegacyApplicationConfigError(
                f"{context} requires string keys"
            )
        # Python dict overwrite preserves the original insertion position,
        # matching PHP array behavior for a repeated existing string key.
        result[entry.key.value] = entry.value
    return result
