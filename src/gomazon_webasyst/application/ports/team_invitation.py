from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationPrepared,
    TeamInvitationRequest,
    TeamInvitationStoreResult,
)
from gomazon_webasyst.contracts.team import TeamTextValue


class TeamInvitationStore(Protocol):
    async def prepare(
        self,
        *,
        actor_contact_id: int,
        request: TeamInvitationRequest,
        manageable_group_ids: tuple[int, ...],
    ) -> TeamInvitationStoreResult: ...

    async def delete_token(self, token: str) -> None: ...


class TeamInvitationValidator(Protocol):
    def email_errors(self, value: str) -> tuple[str, ...]: ...

    def phone_errors(self, value: str) -> tuple[str, ...]: ...


class TeamInvitationHook(Protocol):
    async def messages(
        self,
        *,
        email: TeamTextValue,
        phone: TeamTextValue,
        groups: tuple[str, ...],
    ) -> tuple[str, ...]: ...


class TeamInvitationLinkBuilder(Protocol):
    def build(self, token: str) -> str: ...


@dataclass(slots=True, frozen=True)
class TeamInvitationEmailSent:
    pass


@dataclass(slots=True, frozen=True)
class TeamInvitationEmailSoftFailure:
    pass


@dataclass(slots=True, frozen=True)
class TeamInvitationEmailRejected:
    description: str


TeamInvitationEmailResult: TypeAlias = (
    TeamInvitationEmailSent
    | TeamInvitationEmailSoftFailure
    | TeamInvitationEmailRejected
)


class TeamInvitationEmailSender(Protocol):
    async def send(
        self,
        invitation: TeamInvitationPrepared,
        *,
        email: str,
        actor_contact_id: int,
    ) -> TeamInvitationEmailResult: ...


class WaidDisconnected:
    pass


class WaidConnected:
    pass


WaidConnection = WaidDisconnected | WaidConnected


class WaidInvitationCodeIssued:
    def __init__(self, code: str, expires_at: int) -> None:
        self.code = code
        self.expires_at = expires_at


class WaidInvitationCodeRejected:
    def __init__(
        self,
        *,
        error: str,
        description: str,
        delay: tuple[int, ...] = (),
    ) -> None:
        self.error = error
        self.description = description
        self.delay = delay


WaidInvitationCodeResult = (
    WaidInvitationCodeIssued | WaidInvitationCodeRejected
)


class TeamWaidInvitationGateway(Protocol):
    def connection(self) -> WaidConnection: ...

    async def installation_code(
        self,
        token: str,
    ) -> WaidInvitationCodeResult: ...
