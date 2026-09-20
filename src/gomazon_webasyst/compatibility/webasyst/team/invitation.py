import re
from typing import TypeAlias
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
    TeamInvitationEmailRejected,
    TeamInvitationEmailResult,
    TeamInvitationEmailSender,
    TeamInvitationHook,
    TeamInvitationLinkBuilder,
    TeamInvitationValidator,
    TeamWaidInvitationGateway,
    WaidDisconnected,
    WaidInvitationCodeResult,
)
from gomazon_webasyst.compatibility.webasyst.api.services.parameter_reader import (
    ApiParameterRead,
    ApiParameterReaderService,
    ApiParameterRejected,
)
from gomazon_webasyst.contracts.team import (
    TeamTextMissing,
    TeamTextPresent,
    TeamTextValue,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationCodeRequest,
    TeamInvitationEmailLinkRequest,
    TeamInvitationPhoneLinkRequest,
    TeamInvitationPrepared,
    TeamInvitationRequest,
)


TeamInvitationRequestParseResult: TypeAlias = (
    TeamInvitationRequest | ApiParameterRejected
)

_PHONE = re.compile(r"^[0-9\-\(\)/\+\s]*$")


class LegacyTeamInvitationRequestParser:
    def __init__(self) -> None:
        self._reader = ApiParameterReaderService()

    def parse(
        self,
        parameters: ApiRequestParameters,
    ) -> TeamInvitationRequestParseResult:
        form = parameters.form.values
        groups = self._groups(form)
        integer_groups = tuple(
            int(item)
            for item in groups
            if self._wa_is_int(item)
        )
        invitation_type = self._scalar(form.get("type", ""))
        email = self._scalar(form.get("email", ""))
        phone = self._scalar(form.get("phone", ""))

        if invitation_type == "code":
            return TeamInvitationCodeRequest(
                email=(
                    TeamTextPresent(value=email)
                    if self._php_truthy(email)
                    else TeamTextMissing()
                ),
                phone=(
                    TeamTextPresent(value=phone)
                    if self._php_truthy(phone)
                    else TeamTextMissing()
                ),
                requested_groups=groups,
                integer_group_ids=integer_groups,
            )

        if self._php_truthy(phone):
            return TeamInvitationPhoneLinkRequest(
                phone=phone,
                requested_groups=groups,
                integer_group_ids=integer_groups,
            )

        read = self._reader.post(
            parameters,
            "email",
            required=True,
        )
        if isinstance(read, ApiParameterRejected):
            return read
        assert isinstance(read, ApiParameterRead)
        return TeamInvitationEmailLinkRequest(
            email=self._scalar(read.value),
            send=self._send(form.get("send", "")),
            requested_groups=groups,
            integer_group_ids=integer_groups,
        )

    @classmethod
    def _groups(cls, form) -> tuple[str, ...]:
        for key in ("groups[]", "groups"):
            if key not in form:
                continue
            value = form[key]
            if isinstance(value, tuple):
                return tuple(cls._scalar(item).strip() for item in value)
            if isinstance(value, dict):
                return ()
            return (cls._scalar(value).strip(),)
        return ()

    @classmethod
    def _send(cls, value: ApiParameterValue) -> bool:
        if isinstance(value, tuple | dict):
            normalized = ""
        else:
            normalized = cls._scalar(value).strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        return cls._php_truthy(normalized)

    @staticmethod
    def _scalar(value: ApiParameterValue) -> str:
        if isinstance(value, tuple | dict):
            return "Array"
        if isinstance(value, bool):
            return "1" if value else ""
        return str(value)

    @staticmethod
    def _php_truthy(value: str) -> bool:
        return value not in {"", "0"}

    @staticmethod
    def _wa_is_int(value: str) -> bool:
        return re.fullmatch(r"\d+|-\d+", value) is not None


class LegacyTeamInvitationValidator(TeamInvitationValidator):
    def email_errors(self, value: str) -> tuple[str, ...]:
        if not value:
            return ("email_required",)
        if not self._valid_email(value):
            return ("email_invalid",)
        return ()

    def phone_errors(self, value: str) -> tuple[str, ...]:
        if not value:
            return ("phone_required",)
        if _PHONE.fullmatch(value) is None:
            return ("phone_invalid",)
        return ()

    @staticmethod
    def _valid_email(value: str) -> bool:
        if len(value) > 255 or value.count("@") != 1:
            return False
        local, domain = value.rsplit("@", 1)
        if not local or len(local) > 64 or not domain:
            return False
        if local.startswith(".") or local.endswith(".") or ".." in local:
            return False
        if any(char.isspace() for char in value):
            return False
        try:
            domain = domain.encode("idna").decode("ascii")
        except UnicodeError:
            return False
        labels = domain.split(".")
        if len(labels) < 2:
            return False
        if any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or re.fullmatch(r"[A-Za-z0-9-]+", label) is None
            for label in labels
        ):
            return False
        return re.fullmatch(
            r"[A-Za-z0-9!#$%&'*+/=?^_{|}~.-]+",
            local,
        ) is not None


class LegacyTeamInvitationHook(TeamInvitationHook):
    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher

    async def messages(
        self,
        *,
        email: TeamTextValue,
        phone: TeamTextValue,
        groups: tuple[str, ...],
    ) -> tuple[str, ...]:
        report = await self._publisher.publish(
            EventDispatchRequest(
                event=EventKey(
                    AppId("team"),
                    EventName("invite_user"),
                ),
                payload=LegacyEventPayload(
                    value={
                        "email": self._text(email),
                        "phone": self._text(phone),
                        "groups": list(groups),
                    }
                ),
            )
        )
        messages: list[str] = []
        for result in report.results:
            if not isinstance(result.value, LegacyEventPayload):
                continue
            value = result.value.value
            if not self._php_truthy_value(value):
                continue
            messages.append(self._php_string(value))
        return tuple(messages)

    @staticmethod
    def _text(value: TeamTextValue):
        if isinstance(value, TeamTextPresent):
            return value.value
        assert isinstance(value, TeamTextMissing)
        return None

    @staticmethod
    def _php_truthy_value(value) -> bool:
        if value is None or value is False:
            return False
        if isinstance(value, int | float):
            return value != 0
        if isinstance(value, str):
            return value not in {"", "0"}
        if isinstance(value, list | dict):
            return bool(value)
        return True

    @staticmethod
    def _php_string(value) -> str:
        if value is True:
            return "1"
        if isinstance(value, list | dict):
            return "Array"
        return str(value)


class LegacyTeamInvitationLinkBuilder(TeamInvitationLinkBuilder):
    def __init__(self, public_root_url: str) -> None:
        self._root = public_root_url.rstrip("/") + "/"

    def build(self, token: str) -> str:
        encoded = quote_plus(token, safe="").replace("~", "%7E")
        return f"{self._root}link.php/{encoded}/"


class UnavailableTeamInvitationEmailSender(TeamInvitationEmailSender):
    async def send(
        self,
        invitation: TeamInvitationPrepared,
        *,
        email: str,
        actor_contact_id: int,
    ) -> TeamInvitationEmailResult:
        del invitation, email, actor_contact_id
        return TeamInvitationEmailRejected(
            "Invitation email delivery adapter is not configured."
        )


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
