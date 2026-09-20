import re
from urllib.parse import quote_plus

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterValue,
    ApiRequestParameters,
)
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.vo.identity import EventKey, EventName
from gomazon_webasyst.application.events.vo.payload import LegacyEventPayload
from gomazon_webasyst.application.ports.event_publisher import EventPublisher
from gomazon_webasyst.application.ports.team_invitation import (
    TeamInvitationEmailSender,
    TeamInvitationHook,
    TeamInvitationLinkBuilder,
    TeamInvitationValidator,
    TeamWaidInvitationGateway,
    WaidDisconnected,
    WaidInvitationCodeResult,
)
from gomazon_webasyst.contracts.enums import TeamInvitationMode
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationPrepared,
    TeamInvitationRequest,
)


_PHONE = re.compile(r"^[0-9\-\(\)/\+\s]*$")


class LegacyTeamInvitationRequestParser:
    def parse(self, parameters: ApiRequestParameters) -> TeamInvitationRequest:
        form = parameters.form.values
        invitation_type = self._scalar(form.get("type", ""))
        mode = (
            TeamInvitationMode.CODE
            if invitation_type == "code"
            else TeamInvitationMode.LINK
        )
        return TeamInvitationRequest(
            mode=mode,
            email=self._scalar(form.get("email", "")),
            phone=self._scalar(form.get("phone", "")),
            group_ids=self._groups(form),
            send=self._send(form.get("send", "")),
        )

    @classmethod
    def _groups(cls, form) -> tuple[int, ...]:
        value: ApiParameterValue = ()
        for key in ("groups[]", "groups"):
            if key in form:
                value = form[key]
                break
        values = value if isinstance(value, tuple) else (value,)
        result: list[int] = []
        for item in values:
            if isinstance(item, str):
                normalized = item.strip()
            elif isinstance(item, int):
                normalized = str(item)
            else:
                continue
            if re.fullmatch(r"-?\d+", normalized):
                result.append(int(normalized))
        return tuple(result)

    @classmethod
    def _send(cls, value: ApiParameterValue) -> bool:
        normalized = cls._scalar(value).strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        return normalized not in {"", "0"}

    @staticmethod
    def _scalar(value: ApiParameterValue) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "1" if value else ""
        if isinstance(value, int | float):
            return str(value)
        return ""


class LegacyTeamInvitationValidator(TeamInvitationValidator):
    def email_errors(self, value: str) -> tuple[str, ...]:
        if not value:
            return ("email_required",)
        if value.count("@") != 1:
            return ("email_invalid",)
        local, domain = value.rsplit("@", 1)
        if not local or not domain or any(ch.isspace() for ch in value):
            return ("email_invalid",)
        return ()

    def phone_errors(self, value: str) -> tuple[str, ...]:
        if not value:
            return ("phone_required",)
        if _PHONE.fullmatch(value) is None:
            return ("phone_invalid",)
        return ()


class LegacyTeamInvitationHook(TeamInvitationHook):
    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher

    async def messages(
        self,
        *,
        email: str,
        phone: str,
        group_ids: tuple[int, ...],
    ) -> tuple[str, ...]:
        report = await self._publisher.publish(
            EventDispatchRequest(
                event=EventKey(
                    AppId("team"),
                    EventName("invite_user"),
                ),
                payload=LegacyEventPayload(
                    value={
                        "email": email if email else None,
                        "phone": phone if phone else None,
                        "groups": list(group_ids),
                    }
                ),
            )
        )
        messages: list[str] = []
        for result in report.results:
            if not isinstance(result.value, LegacyEventPayload):
                continue
            value = result.value.value
            if value in {"", 0, False, None}:
                continue
            messages.append(str(value))
        return tuple(messages)


class LegacyTeamInvitationLinkBuilder(TeamInvitationLinkBuilder):
    def __init__(self, public_root_url: str) -> None:
        self._root = public_root_url.rstrip("/") + "/"

    def build(self, token: str) -> str:
        encoded = quote_plus(token, safe="").replace("~", "%7E")
        return f"{self._root}link.php/{encoded}/"


class NoopTeamInvitationEmailSender(TeamInvitationEmailSender):
    async def send(
        self,
        invitation: TeamInvitationPrepared,
        *,
        email: str,
        actor_contact_id: int,
    ) -> None:
        del invitation, email, actor_contact_id


class DisconnectedTeamWaidInvitationGateway(TeamWaidInvitationGateway):
    def connection(self) -> WaidDisconnected:
        return WaidDisconnected()

    async def installation_code(
        self,
        token: str,
    ) -> WaidInvitationCodeResult:
        raise RuntimeError(
            f"WAID installation code requested while disconnected: {token}"
        )
