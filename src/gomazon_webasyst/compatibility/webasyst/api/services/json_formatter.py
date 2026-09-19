import json
from collections.abc import Mapping


def _clean(value):
    if isinstance(value, Mapping):
        return {
            str(key): _clean(item)
            for key, item in value.items()
            if key != "_element"
        }
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


class LegacyJsonApiFormatter:
    def format(self, payload: object) -> str:
        return json.dumps(
            _clean(payload),
            ensure_ascii=False,
            separators=(",", ":"),
        )
