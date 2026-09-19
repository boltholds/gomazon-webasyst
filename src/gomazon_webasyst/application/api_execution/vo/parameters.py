from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, TypeAlias


ApiParameterValue: TypeAlias = (
    str
    | int
    | float
    | bool
    | tuple["ApiParameterValue", ...]
    | Mapping[str, "ApiParameterValue"]
)


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"unsupported API parameter value: {type(value).__name__}")


@dataclass(slots=True, frozen=True)
class ApiParameterMap:
    values: Mapping[str, ApiParameterValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "values",
            MappingProxyType({str(key): _freeze(value) for key, value in self.values.items()}),
        )

    def __getitem__(self, key: str) -> ApiParameterValue:
        return self.values[key]

    def __contains__(self, key: object) -> bool:
        return key in self.values


@dataclass(slots=True, frozen=True)
class ApiRequestParameters:
    query: ApiParameterMap
    form: ApiParameterMap
