from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.runtime.vo.dispatch import (
    DispatchRuntimeDefinition,
)


@dataclass(slots=True, frozen=True)
class DispatchRegistrationAvailable:
    definition: DispatchRuntimeDefinition


@dataclass(slots=True, frozen=True)
class DispatchRegistrationConflict:
    definition: DispatchRuntimeDefinition


DispatchRegistrationCheck: TypeAlias = (
    DispatchRegistrationAvailable | DispatchRegistrationConflict
)


@dataclass(slots=True, frozen=True)
class DispatchRegistered:
    definition: DispatchRuntimeDefinition


@dataclass(slots=True, frozen=True)
class DispatchRegistrationRejected:
    definition: DispatchRuntimeDefinition


DispatchRegistrationResult: TypeAlias = (
    DispatchRegistered | DispatchRegistrationRejected
)


class DispatchRegistrationSink(Protocol):
    def check(
        self,
        definition: DispatchRuntimeDefinition,
    ) -> DispatchRegistrationCheck: ...

    def register(
        self,
        definition: DispatchRuntimeDefinition,
    ) -> DispatchRegistrationResult: ...
