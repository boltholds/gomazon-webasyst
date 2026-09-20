from gomazon_webasyst.presentation.http.legacy_api import (
    _parameter_map_from_pairs,
)


def test_parameter_pairs_preserve_repeated_form_values() -> None:
    result = _parameter_map_from_pairs(
        (
            ("groups[]", " 2 "),
            ("groups[]", "3"),
            ("send", "false"),
        )
    )

    assert result["groups[]"] == (" 2 ", "3")
    assert result["send"] == "false"
