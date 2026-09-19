import ast
from pathlib import Path

import pytest

from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    LegacyPhpConfigError,
    LegacyPhpConfigLimitError,
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayAutoKey,
    PhpArrayIntKey,
    PhpArrayStringKey,
    PhpNull,
)


def _mapping(value: PhpArray) -> dict[str | int, object]:
    result: dict[str | int, object] = {}
    for entry in value.entries:
        if isinstance(entry.key, PhpArrayStringKey):
            result[entry.key.value] = entry.value
        elif isinstance(entry.key, PhpArrayIntKey):
            result[entry.key.value] = entry.value
    return result


def test_parses_long_array_scalars_nested_values_comments_and_trailing_comma() -> None:
    value = parse_php_return_value(
        """<?php
        // source comment
        return array(
            'name' => 'Site',
            'enabled' => true,
            'disabled' => false,
            'count' => 3,
            'ratio' => 1.5,
            'nothing' => null,
            'nested' => array('key' => 'value',),
        );
        """
    )
    assert isinstance(value, PhpArray)
    values = _mapping(value)
    assert values["name"] == "Site"
    assert values["enabled"] is True
    assert values["disabled"] is False
    assert values["count"] == 3
    assert values["ratio"] == 1.5
    assert isinstance(values["nothing"], PhpNull)
    assert isinstance(values["nested"], PhpArray)
    assert _mapping(values["nested"])["key"] == "value"  # type: ignore[arg-type]


def test_parses_short_array_integer_keys_and_unkeyed_entries() -> None:
    value = parse_php_return_value(
        """<?php
        # another comment
        return [
            16 => 'img/icon16.png',
            48 => 'img/icon48.png',
            'tail',
        ];
        """
    )
    assert isinstance(value, PhpArray)
    assert isinstance(value.entries[0].key, PhpArrayIntKey)
    assert value.entries[0].key.value == 16
    assert isinstance(value.entries[1].key, PhpArrayIntKey)
    assert value.entries[1].key.value == 48
    assert isinstance(value.entries[2].key, PhpArrayAutoKey)
    assert value.entries[2].value == "tail"


def test_parses_supported_string_escapes_without_interpolation() -> None:
    value = parse_php_return_value(
        r"""<?php return [
            'single' => 'it\'s ok',
            "double" => "line\nvalue",
        ];"""
    )
    assert isinstance(value, PhpArray)
    values = _mapping(value)
    assert values["single"] == "it's ok"
    assert values["double"] == "line\nvalue"


@pytest.mark.parametrize(
    "source",
    [
        "<?php return some_function();",
        "<?php return $config;",
        "<?php return ['name' => 'A'.'B'];",
        "<?php return include 'other.php';",
        "<?php require 'bootstrap.php'; return [];",
        "<?php echo 'side effect'; return [];",
        '<?php return ["name" => "$dynamic"];',
    ],
)
def test_rejects_dynamic_or_executable_php(source: str) -> None:
    with pytest.raises(LegacyPhpConfigError):
        parse_php_return_value(source)


@pytest.mark.parametrize(
    "source",
    [
        "<?php return ['name' => 'unterminated];",
        "<?php return array('name' => 'x';",
        "<?php return [1 => ];",
        "<?php return []; trailing",
    ],
)
def test_rejects_malformed_or_trailing_input(source: str) -> None:
    with pytest.raises(LegacyPhpConfigError):
        parse_php_return_value(source)


def test_enforces_size_depth_token_and_entry_limits() -> None:
    with pytest.raises(LegacyPhpConfigLimitError):
        parse_php_return_value("<?php return ['name' => 'value'];", max_bytes=8)

    nested = "<?php return " + "[" * 8 + "'x'" + "]" * 8 + ";"
    with pytest.raises(LegacyPhpConfigLimitError):
        parse_php_return_value(nested, max_depth=4)

    with pytest.raises(LegacyPhpConfigLimitError):
        parse_php_return_value(
            "<?php return ['a'=>1,'b'=>2,'c'=>3];",
            max_entries=2,
        )

    with pytest.raises(LegacyPhpConfigLimitError):
        parse_php_return_value(
            "<?php return ['a'=>1,'b'=>2,'c'=>3];",
            max_tokens=4,
        )


def test_parser_package_contains_no_execution_or_dynamic_import_primitives() -> None:
    root = Path(
        "src/gomazon_webasyst/compatibility/webasyst/application_registry"
    )
    if not root.exists():
        raise AssertionError("application registry compatibility package is missing")

    forbidden_calls = {"eval", "exec", "__import__"}
    forbidden_modules = {"subprocess", "importlib"}
    violations: list[str] = []

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in forbidden_calls:
                    violations.append(f"{path}:{node.lineno}:{node.func.id}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in forbidden_modules:
                        violations.append(f"{path}:{node.lineno}:{alias.name}")
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".", 1)[0]
                if module in forbidden_modules:
                    violations.append(f"{path}:{node.lineno}:{node.module}")

    assert violations == []
