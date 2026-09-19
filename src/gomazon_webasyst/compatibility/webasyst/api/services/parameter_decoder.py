from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.contracts.enums import LegacyApiParameterDecodeReason


@dataclass(slots=True, frozen=True)
class LegacyApiParametersDecoded:
    parameters: ApiParameterMap


@dataclass(slots=True, frozen=True)
class LegacyApiParameterDecodeRejected:
    reason: LegacyApiParameterDecodeReason
    key: str


LegacyApiParameterDecodeResult: TypeAlias = (
    LegacyApiParametersDecoded | LegacyApiParameterDecodeRejected
)


@dataclass(slots=True, frozen=True)
class _KeySegment:
    value: str


@dataclass(slots=True, frozen=True)
class _AppendSegment:
    pass


_PathSegment: TypeAlias = _KeySegment | _AppendSegment


@dataclass(slots=True, frozen=True)
class _InsertSucceeded:
    pass


class _ScalarNode:
    def __init__(self, value: str) -> None:
        self.value = value


class _MapNode:
    def __init__(self) -> None:
        self.values: dict[str, _Node] = {}


class _ListNode:
    def __init__(self) -> None:
        self.values: list[_Node] = []


_Node: TypeAlias = _ScalarNode | _MapNode | _ListNode


class LegacyApiParameterDecoder:
    def __init__(
        self,
        *,
        max_depth: int = 8,
        max_entries: int = 1024,
        max_key_length: int = 256,
        max_value_length: int = 65536,
    ) -> None:
        if min(max_depth, max_entries, max_key_length, max_value_length) <= 0:
            raise ValueError("legacy API parameter decoder limits must be positive")
        self._max_depth = max_depth
        self._max_entries = max_entries
        self._max_key_length = max_key_length
        self._max_value_length = max_value_length

    def decode(
        self,
        pairs: tuple[tuple[str, str], ...],
    ) -> LegacyApiParameterDecodeResult:
        if len(pairs) > self._max_entries:
            return LegacyApiParameterDecodeRejected(
                LegacyApiParameterDecodeReason.ENTRY_LIMIT,
                "",
            )

        root = _MapNode()
        for raw_key, value in pairs:
            if len(raw_key) > self._max_key_length:
                return LegacyApiParameterDecodeRejected(
                    LegacyApiParameterDecodeReason.KEY_LENGTH_LIMIT,
                    raw_key,
                )
            if len(value) > self._max_value_length:
                return LegacyApiParameterDecodeRejected(
                    LegacyApiParameterDecodeReason.VALUE_LENGTH_LIMIT,
                    raw_key,
                )
            path = self._parse_key(raw_key)
            if isinstance(path, LegacyApiParameterDecodeRejected):
                return path
            if len(path) > self._max_depth:
                return LegacyApiParameterDecodeRejected(
                    LegacyApiParameterDecodeReason.DEPTH_LIMIT,
                    raw_key,
                )
            rejected = self._insert(root, path, value, raw_key)
            if isinstance(rejected, LegacyApiParameterDecodeRejected):
                return rejected

        return LegacyApiParametersDecoded(
            ApiParameterMap(self._materialize_map(root))
        )

    def _parse_key(
        self,
        raw_key: str,
    ) -> tuple[_PathSegment, ...] | LegacyApiParameterDecodeRejected:
        if not raw_key:
            return LegacyApiParameterDecodeRejected(
                LegacyApiParameterDecodeReason.MALFORMED_KEY,
                raw_key,
            )
        bracket = raw_key.find("[")
        if bracket < 0:
            return (_KeySegment(raw_key),)

        base = raw_key[:bracket]
        if not base:
            return LegacyApiParameterDecodeRejected(
                LegacyApiParameterDecodeReason.MALFORMED_KEY,
                raw_key,
            )

        segments: list[_PathSegment] = [_KeySegment(base)]
        index = bracket
        while index < len(raw_key):
            if raw_key[index] != "[":
                return LegacyApiParameterDecodeRejected(
                    LegacyApiParameterDecodeReason.MALFORMED_KEY,
                    raw_key,
                )
            close = raw_key.find("]", index + 1)
            if close < 0:
                return LegacyApiParameterDecodeRejected(
                    LegacyApiParameterDecodeReason.MALFORMED_KEY,
                    raw_key,
                )
            value = raw_key[index + 1 : close]
            if value:
                segments.append(_KeySegment(value))
            else:
                segments.append(_AppendSegment())
            index = close + 1
        return tuple(segments)

    def _insert(
        self,
        root: _MapNode,
        path: tuple[_PathSegment, ...],
        value: str,
        raw_key: str,
    ) -> LegacyApiParameterDecodeRejected | _InsertSucceeded:
        current: _Node = root
        for index, segment in enumerate(path):
            last = index == len(path) - 1
            next_segment = path[index + 1] if not last else _KeySegment("")

            if isinstance(segment, _KeySegment):
                if not isinstance(current, _MapNode):
                    return self._shape_conflict(raw_key)
                if last:
                    existing = current.values.get(segment.value)
                    if existing is not None and not isinstance(existing, _ScalarNode):
                        return self._shape_conflict(raw_key)
                    current.values[segment.value] = _ScalarNode(value)
                    return _InsertSucceeded()

                expected_list = isinstance(next_segment, _AppendSegment)
                existing = current.values.get(segment.value)
                if existing is None:
                    child: _Node = _ListNode() if expected_list else _MapNode()
                    current.values[segment.value] = child
                    current = child
                    continue
                if expected_list and not isinstance(existing, _ListNode):
                    return self._shape_conflict(raw_key)
                if not expected_list and not isinstance(existing, _MapNode):
                    return self._shape_conflict(raw_key)
                current = existing
                continue

            if not isinstance(current, _ListNode):
                return self._shape_conflict(raw_key)
            if not last:
                return LegacyApiParameterDecodeRejected(
                    LegacyApiParameterDecodeReason.MALFORMED_KEY,
                    raw_key,
                )
            current.values.append(_ScalarNode(value))
            return _InsertSucceeded()

        raise AssertionError("parameter path must not be empty")

    @staticmethod
    def _shape_conflict(raw_key: str) -> LegacyApiParameterDecodeRejected:
        return LegacyApiParameterDecodeRejected(
            LegacyApiParameterDecodeReason.SHAPE_CONFLICT,
            raw_key,
        )

    def _materialize_map(self, node: _MapNode) -> dict[str, object]:
        return {
            key: self._materialize(value)
            for key, value in node.values.items()
        }

    def _materialize(self, node: _Node):
        if isinstance(node, _ScalarNode):
            return node.value
        if isinstance(node, _ListNode):
            return tuple(self._materialize(value) for value in node.values)
        if isinstance(node, _MapNode):
            return self._materialize_map(node)
        raise AssertionError("unsupported parameter node")
