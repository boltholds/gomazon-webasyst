from dataclasses import fields

from gomazon_webasyst.composition.container import Container


def test_container_exposes_oauth_authorization_component() -> None:
    assert "oauth_authorization" in {field.name for field in fields(Container)}
