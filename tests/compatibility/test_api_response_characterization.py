import json
import xml.etree.ElementTree as ET

from gomazon_webasyst.compatibility.webasyst.api.services.json_formatter import LegacyJsonApiFormatter
from gomazon_webasyst.compatibility.webasyst.api.services.xml_formatter import LegacyXmlApiFormatter


def test_source_backed_json_decorator_removes_element_keys_at_all_levels() -> None:
    data = {"_element": "x", "nested": {"_element": "y", "value": 1}}
    assert json.loads(LegacyJsonApiFormatter().format(data)) == {"nested": {"value": 1}}


def test_source_backed_xml_decorator_uses_response_root_and_category_singularization() -> None:
    root = ET.fromstring(
        LegacyXmlApiFormatter().format({"categories": [{"name": "A"}, {"name": "B"}]})
    )
    assert root.tag == "response"
    assert [child.tag for child in root.find("categories")] == ["category", "category"]
