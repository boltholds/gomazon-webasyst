import pytest

from gomazon_webasyst.application.api_execution.vo.origin import ApiRequestOrigin


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/relative/",
        "example.com",
        "ftp://example.com/",
        "https://example.com/path?x=1",
        "https://example.com/path#fragment",
    ],
)
def test_api_request_origin_rejects_non_absolute_or_stateful_urls(value: str) -> None:
    with pytest.raises(ValueError):
        ApiRequestOrigin(value)


def test_api_request_origin_normalizes_scheme_and_trailing_slash() -> None:
    assert ApiRequestOrigin("HTTPS://example.com").value == "https://example.com/"
    assert ApiRequestOrigin("https://example.com/root").value == "https://example.com/root/"
