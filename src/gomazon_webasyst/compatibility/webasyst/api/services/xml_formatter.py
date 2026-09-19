from collections.abc import Mapping, Sequence
import xml.etree.ElementTree as ET


def _is_array(value: object) -> bool:
    return isinstance(value, (Mapping, list, tuple))


def _is_int_key(key: object) -> bool:
    return isinstance(key, int) and not isinstance(key, bool)


def _iter_array(value: object):
    if isinstance(value, Mapping):
        return list(value.items())
    if isinstance(value, (list, tuple)):
        return list(enumerate(value))
    raise TypeError("expected array-like value")


def _has_nonsequential_keys(value: object) -> bool:
    if isinstance(value, (list, tuple)):
        return False
    if not isinstance(value, Mapping):
        return False
    expected = 0
    for key in value.keys():
        if key != expected:
            return True
        expected += 1
    return False


def _first_value(value: object):
    items = _iter_array(value)
    if not items:
        return ""
    return items[0][1]


def _singular(key: str) -> str:
    if key.endswith("ies"):
        return key[:-3] + "y"
    if key.endswith("s"):
        return key[:-1]
    return ""


class LegacyXmlApiFormatter:
    def format(self, payload: object) -> str:
        root = ET.Element("response")
        if _is_array(payload):
            self._parse_array(root, payload)
        else:
            root.text = str(payload)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def _parse_array(
        self,
        context: ET.Element,
        array: object,
        list_item_name: str = "",
    ) -> None:
        if (
            not list_item_name
            and isinstance(array, Mapping)
            and "_element" in array
        ):
            list_item_name = str(array["_element"])

        for key, value in _iter_array(array):
            if key == "_element":
                continue
            if not _is_int_key(key) and not _is_array(value):
                self._create_node(context, str(key), value)
                continue
            if not _is_int_key(key) and _is_array(value):
                key_text = str(key)
                first = _first_value(value)
                sub_key = (
                    _singular(key_text)
                    if _is_array(first) and key_text.endswith("s")
                    else ""
                )
                if _has_nonsequential_keys(value) or sub_key:
                    element = ET.SubElement(context, key_text)
                    self._parse_array(element, value, sub_key)
                else:
                    self._parse_array(context, value, key_text)
                continue
            if _is_int_key(key) and _is_array(value):
                if list_item_name:
                    element = ET.SubElement(context, list_item_name)
                    self._parse_array(element, value)
                else:
                    self._parse_array(context, value)
                continue
            if _is_int_key(key) and not _is_array(value) and list_item_name:
                self._create_node(context, list_item_name, value)

    @staticmethod
    def _create_node(context: ET.Element, name: str, value: object) -> None:
        element = ET.SubElement(context, name)
        text = str(value)
        if text:
            element.text = text
