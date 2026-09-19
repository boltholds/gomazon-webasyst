import pytest

from gomazon_webasyst.compatibility.webasyst.api.services.parameter_decoder import (
    LegacyApiParameterDecoder,
    LegacyApiParameterDecodeRejected,
    LegacyApiParametersDecoded,
)
from gomazon_webasyst.contracts.enums import LegacyApiParameterDecodeReason


def decoded(*pairs: tuple[str, str]):
    result = LegacyApiParameterDecoder().decode(tuple(pairs))
    assert isinstance(result, LegacyApiParametersDecoded)
    return result.parameters


def test_decodes_scalar_top_level_parameters_and_last_scalar_wins() -> None:
    params = decoded(("access_token", "one"), ("access_token", "two"))
    assert params["access_token"] == "two"


def test_decodes_nested_group_id_append_values_in_order() -> None:
    params = decoded(
        ("filter[group_id][]", "2"),
        ("filter[group_id][]", "7"),
    )
    assert params["filter"]["group_id"] == ("2", "7")


def test_decodes_access_list_and_associative_forms() -> None:
    list_params = decoded(
        ("filter[access][]", "crm"),
        ("filter[access][]", "files"),
    )
    assert list_params["filter"]["access"] == ("crm", "files")

    map_params = decoded(
        ("filter[access][crm]", "limited"),
        ("filter[access][files]", "full"),
    )
    assert map_params["filter"]["access"] == {
        "crm": "limited",
        "files": "full",
    }


def test_decodes_group_type_list() -> None:
    params = decoded(
        ("filter[type][]", "group"),
        ("filter[type][]", "location"),
    )
    assert params["filter"]["type"] == ("group", "location")


@pytest.mark.parametrize(
    "pairs",
    [
        (("filter", "scalar"), ("filter[group_id][]", "1")),
        (("filter[group_id][]", "1"), ("filter[group_id][x]", "2")),
        (("filter[access][crm]", "limited"), ("filter[access][]", "files")),
    ],
)
def test_rejects_scalar_map_list_shape_collisions(pairs) -> None:
    result = LegacyApiParameterDecoder().decode(pairs)
    assert isinstance(result, LegacyApiParameterDecodeRejected)
    assert result.reason is LegacyApiParameterDecodeReason.SHAPE_CONFLICT


def test_rejects_malformed_bracket_keys() -> None:
    for key in ("[x]", "filter[x", "filter[x]tail", "filter[][x]"):
        result = LegacyApiParameterDecoder().decode(((key, "1"),))
        assert isinstance(result, LegacyApiParameterDecodeRejected)
        assert result.reason is LegacyApiParameterDecodeReason.MALFORMED_KEY


def test_enforces_entry_depth_key_and_value_limits() -> None:
    assert LegacyApiParameterDecoder(max_entries=1).decode(
        (("a", "1"), ("b", "2"))
    ).reason is LegacyApiParameterDecodeReason.ENTRY_LIMIT
    assert LegacyApiParameterDecoder(max_depth=2).decode(
        (("a[b][c]", "1"),)
    ).reason is LegacyApiParameterDecodeReason.DEPTH_LIMIT
    assert LegacyApiParameterDecoder(max_key_length=2).decode(
        (("long", "1"),)
    ).reason is LegacyApiParameterDecodeReason.KEY_LENGTH_LIMIT
    assert LegacyApiParameterDecoder(max_value_length=2).decode(
        (("a", "long"),)
    ).reason is LegacyApiParameterDecodeReason.VALUE_LENGTH_LIMIT
