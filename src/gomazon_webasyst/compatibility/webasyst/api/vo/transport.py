from dataclasses import dataclass
from typing import TypeAlias


@dataclass(slots=True, frozen=True)
class ApiJsonpCallback:
    value: str


@dataclass(slots=True, frozen=True)
class AuthorizationHeader:
    value: str


@dataclass(slots=True, frozen=True)
class NoAuthorizationHeader:
    pass


AuthorizationHeaderState: TypeAlias = AuthorizationHeader | NoAuthorizationHeader


@dataclass(slots=True, frozen=True)
class RequestedResponseFormat:
    value: str


@dataclass(slots=True, frozen=True)
class NoRequestedResponseFormat:
    pass


RequestedResponseFormatState: TypeAlias = RequestedResponseFormat | NoRequestedResponseFormat
