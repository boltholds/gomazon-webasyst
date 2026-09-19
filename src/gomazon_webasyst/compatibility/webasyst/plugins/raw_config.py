from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyApplicationConfigError,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayAutoKey,
    PhpArrayIntKey,
    PhpArrayStringKey,
    PhpValue,
)


def php_array_values(
    value: PhpValue,
    *,
    context: str,
) -> tuple[PhpValue, ...]:
    if not isinstance(value, PhpArray):
        raise LegacyApplicationConfigError(f"{context} must be a PHP array")
    values: list[PhpValue] = []
    for entry in value.entries:
        if not isinstance(
            entry.key,
            (PhpArrayAutoKey, PhpArrayIntKey),
        ):
            raise LegacyApplicationConfigError(
                f"{context} requires list-style array entries"
            )
        values.append(entry.value)
    return tuple(values)


def php_method_names(
    value: PhpValue,
    *,
    context: str,
) -> tuple[str, ...]:
    if isinstance(value, str):
        if not value:
            raise LegacyApplicationConfigError(
                f"{context} method must not be empty"
            )
        return (value,)
    values = php_array_values(value, context=context)
    result: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item:
            raise LegacyApplicationConfigError(
                f"{context} methods must be non-empty strings"
            )
        result.append(item)
    if not result:
        raise LegacyApplicationConfigError(
            f"{context} must contain at least one method"
        )
    return tuple(result)


def php_string_keyed_entries(
    value: PhpValue,
    *,
    context: str,
) -> tuple[tuple[str, PhpValue], ...]:
    if not isinstance(value, PhpArray):
        raise LegacyApplicationConfigError(f"{context} must be a PHP array")
    result: list[tuple[str, PhpValue]] = []
    for entry in value.entries:
        if not isinstance(entry.key, PhpArrayStringKey):
            raise LegacyApplicationConfigError(
                f"{context} requires string keys"
            )
        result.append((entry.key.value, entry.value))
    return tuple(result)
