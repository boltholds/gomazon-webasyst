import json
import xml.etree.ElementTree as ET

import pytest

from gomazon_webasyst.application.api_execution.composites.results import (
    ApiExecutionRejected,
    ApiExecutionSucceeded,
)
from gomazon_webasyst.compatibility.webasyst.api.composites.response_renderer import LegacyApiResponseRenderer
from gomazon_webasyst.compatibility.webasyst.api.services.json_formatter import LegacyJsonApiFormatter
from gomazon_webasyst.compatibility.webasyst.api.services.xml_formatter import LegacyXmlApiFormatter
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import ApiJsonpCallback
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode, ApiResponseFormat


def test_json_formatter_removes_element_metadata_recursively() -> None:
    payload = {
        "_element": "item",
        "items": [
            {"_element": "child", "id": 1},
            {"id": 2},
        ],
    }
    rendered = LegacyJsonApiFormatter().format(payload)
    assert "_element" not in rendered
    assert json.loads(rendered) == {"items": [{"id": 1}, {"id": 2}]}


def test_xml_formatter_respects_element_and_plural_inference() -> None:
    rendered = LegacyXmlApiFormatter().format({
        "items": {
            "_element": "entry",
            0: {"id": 1},
            1: {"id": 2},
        },
        "categories": [
            {"id": 3},
        ],
        "empty": "",
    })
    root = ET.fromstring(rendered)
    assert root.tag == "response"
    assert [node.tag for node in root.find("items")] == ["entry", "entry"]
    assert root.find("items/entry/id").text == "1"
    assert root.find("categories/category/id").text == "3"
    assert root.find("empty") is not None
    assert root.find("empty").text is None


@pytest.mark.parametrize("callback", ["", "0"])
def test_php_falsy_callback_does_not_enable_jsonp(callback: str) -> None:
    response = LegacyApiResponseRenderer().render(
        ApiExecutionSucceeded(payload={"ok": True}, status_code=201),
        ApiResponseFormat.JSON,
        ApiJsonpCallback(callback),
    )
    assert response.status_code == 201
    assert response.media_type == "application/json; charset=utf-8"


def test_nonempty_jsonp_callback_forces_200_even_for_error() -> None:
    response = LegacyApiResponseRenderer().render(
        ApiExecutionRejected(
            error=ApiFrameworkError(
                code=ApiFrameworkErrorCode.ACCESS_DENIED,
                description="Denied",
                http_status=403,
                details={"app": "shop"},
            )
        ),
        ApiResponseFormat.JSON,
        ApiJsonpCallback("cb"),
    )
    assert response.status_code == 200
    assert response.media_type == "text/javascript; charset=utf-8"
    assert response.body.startswith("cb(")
    assert response.body.endswith(");")
    payload = json.loads(response.body[3:-2])
    assert payload == {
        "error": "access_denied",
        "app": "shop",
        "error_description": "Denied",
    }


def test_xml_error_uses_legacy_error_payload() -> None:
    response = LegacyApiResponseRenderer().render(
        ApiExecutionRejected(
            error=ApiFrameworkError(
                code=ApiFrameworkErrorCode.INVALID_METHOD,
                description="Unknown method",
                http_status=404,
                details={},
            )
        ),
        ApiResponseFormat.XML,
        ApiJsonpCallback("ignored"),
    )
    root = ET.fromstring(response.body)
    assert response.status_code == 404
    assert response.media_type == "text/xml; charset=utf-8"
    assert root.find("error").text == "invalid_method"
    assert root.find("error_description").text == "Unknown method"
