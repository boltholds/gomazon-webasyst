import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias
from urllib.parse import quote_plus, urlsplit, urlunsplit

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
    TeamInvitationGroupsPayload,
    TeamInvitationPhoneLinkRequest,
    TeamInvitationPrepared,
    TeamInvitationRequest,
)


TeamInvitationRequestParseResult: TypeAlias = (
    TeamInvitationRequest | ApiParameterRejected
)

_GROUP_KEY = re.compile(r"^groups((?:\[[^\]]*\])*)$")


@dataclass(slots=True, frozen=True)
class _ParsedInvitationGroups:
    payload: TeamInvitationGroupsPayload
    scalar_values: tuple[str, ...]


_PHONE = re.compile(r"^[0-9\-\(\)/\+\s]*$")
_EMAIL = re.compile(
    r"^(?!(?:(?:\x22?\x5C[\x00-\x7E]\x22?)|(?:\x22?[^\x5C\x22]\x22?)){255,})"
    r"(?!(?:(?:\x22?\x5C[\x00-\x7E]\x22?)|(?:\x22?[^\x5C\x22]\x22?)){65,}@)"
    r"(?:(?:[\x21\x23-\x27\x2A\x2B\x2D\x2F-\x39\x3D\x3F\x5E-\x7E]+)|"
    r"(?:\x22(?:[\x01-\x08\x0B\x0C\x0E-\x1F\x21\x23-\x5B\x5D-\x7F]|(?:\x5C[\x00-\x7F]))*\x22))"
    r"(?:\.(?:(?:[\x21\x23-\x27\x2A\x2B\x2D\x2F-\x39\x3D\x3F\x5E-\x7E]+)|"
    r"(?:\x22(?:[\x01-\x08\x0B\x0C\x0E-\x1F\x21\x23-\x5B\x5D-\x7F]|(?:\x5C[\x00-\x7F]))*\x22)))*"
    r"@(?:(?:(?!.*[^.]{64,})(?:(?:[a-z0-9](?:[\-a-z0-9]*[a-z0-9])*\.){1,126}){1,}"
    r"(?:(?:[a-z][a-z0-9]*)|(?:(?:xn--)[a-z0-9]+))(?:-[a-z0-9]+)*)|"
    r"(?:\[(?:(?:IPv6:(?:(?:[a-f0-9]{1,4}(?::[a-f0-9]{1,4}){7})|"
    r"(?:(?!(?:.*[a-f0-9][:\]]){7,})(?:[a-f0-9]{1,4}(?::[a-f0-9]{1,4}){0,5})?::"
    r"(?:[a-f0-9]{1,4}(?::[a-f0-9]{1,4}){0,5})?)))|"
    r"(?:(?:IPv6:(?:(?:[a-f0-9]{1,4}(?::[a-f0-9]{1,4}){5}:)|"
    r"(?:(?!(?:.*[a-f0-9]:){5,})(?:[a-f0-9]{1,4}(?::[a-f0-9]{1,4}){0,3})?::"
    r"(?:[a-f0-9]{1,4}(?::[a-f0-9]{1,4}){0,3}:)?)))?"
    r"(?:(?:25[0-5])|(?:2[0-4][0-9])|(?:1[0-9]{2})|(?:[1-9]?[0-9]))"
    r"(?:\.(?:(?:25[0-5])|(?:2[0-4][0-9])|(?:1[0-9]{2})|(?:[1-9]?[0-9]))){3}))\]))$",
    re.IGNORECASE,
)


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
            for item in groups.scalar_values
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
                requested_groups=groups.scalar_values,
                integer_group_ids=integer_groups,
                group_payload=groups.payload,
            )

        if self._php_truthy(phone):
            return TeamInvitationPhoneLinkRequest(
                phone=phone,
                requested_groups=groups.scalar_values,
                integer_group_ids=integer_groups,
                group_payload=groups.payload,
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
            requested_groups=groups.scalar_values,
            integer_group_ids=integer_groups,
            group_payload=groups.payload,
        )

    @classmethod
    def _groups(cls, form) -> _ParsedInvitationGroups:
        root: dict[str, object] = {}
        found = False

        for key, raw_value in form.items():
            match = _GROUP_KEY.fullmatch(str(key))
            if match is None:
                continue
            found = True
            suffix = match.group(1)
            segments = tuple(re.findall(r"\[([^\]]*)\]", suffix))

            if not segments:
                root.clear()
                scalar = cls._last_scalar(raw_value).strip()
                root["0"] = scalar
                continue

            values = raw_value if isinstance(raw_value, tuple) else (raw_value,)
            if segments[-1] != "" and values:
                values = (values[-1],)
            for value in values:
                cls._insert_group_value(
                    root,
                    segments,
                    cls._trim_group_value(value),
                )

        if not found:
            return _ParsedInvitationGroups(payload=[], scalar_values=())

        scalar_values = tuple(
            value
            for value in root.values()
            if isinstance(value, str)
        )
        payload = cls._normalize_group_array(root)
        assert isinstance(payload, list | dict)
        return _ParsedInvitationGroups(
            payload=payload,
            scalar_values=scalar_values,
        )

    @classmethod
    def _trim_group_value(cls, value: ApiParameterValue) -> object:
        if isinstance(value, Mapping):
            return {
                str(key): cls._trim_group_value(item)
                for key, item in value.items()
            }
        if isinstance(value, tuple):
            return {
                str(index): cls._trim_group_value(item)
                for index, item in enumerate(value)
            }
        return cls._scalar(value).strip()

    @classmethod
    def _insert_group_value(
        cls,
        container: dict[str, object],
        segments: tuple[str, ...],
        value: object,
    ) -> None:
        current = container
        for index, segment in enumerate(segments):
            key = (
                cls._next_numeric_key(current)
                if segment == ""
                else segment
            )
            is_last = index == len(segments) - 1
            if is_last:
                current[key] = value
                return
            child = current.get(key)
            if not isinstance(child, dict):
                child = {}
                current[key] = child
            current = child

    @staticmethod
    def _next_numeric_key(container: dict[str, object]) -> str:
        numeric = tuple(
            int(key)
            for key in container
            if key.isascii() and key.isdecimal()
        )
        return str(max(numeric, default=-1) + 1)

    @classmethod
    def _normalize_group_array(cls, value: object):
        if not isinstance(value, dict):
            assert isinstance(value, str)
            return value

        normalized = {
            key: cls._normalize_group_array(item)
            for key, item in value.items()
        }
        sequential = [str(index) for index in range(len(normalized))]
        if list(normalized) == sequential:
            return [normalized[key] for key in sequential]
        return normalized

    @classmethod
    def _last_scalar(cls, value: ApiParameterValue) -> str:
        if isinstance(value, tuple):
            if not value:
                return ""
            return cls._last_scalar(value[-1])
        return cls._scalar(value)

    @classmethod
    def _send(cls, value: ApiParameterValue) -> bool:
        if isinstance(value, tuple | Mapping):
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
        if isinstance(value, tuple):
            if not value:
                return ""
            return LegacyTeamInvitationRequestParser._scalar(value[-1])
        if isinstance(value, Mapping):
            return "Array"
        if isinstance(value, bool):
            return "1" if value else ""
        return str(value)

    @staticmethod
    def _php_truthy(value: str) -> bool:
        return value not in {"", "0"}

    @staticmethod
    def _wa_is_int(value: str) -> bool:
        return re.fullmatch(r"[0-9]+|-[0-9]+", value) is not None


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

    @classmethod
    def _valid_email(cls, value: str) -> bool:
        if "<script" in value.casefold():
            return False
        normalized = cls._idna_email(value)
        return _EMAIL.fullmatch(normalized) is not None

    @staticmethod
    def _idna_email(value: str) -> str:
        if "@" not in value:
            return value
        local, domain = value.rsplit("@", 1)
        if domain.startswith("[") and domain.endswith("]"):
            return value
        try:
            encoded_domain = domain.encode("idna").decode("ascii")
        except UnicodeError:
            return value
        return f"{local}@{encoded_domain}"


class LegacyTeamInvitationHook(TeamInvitationHook):
    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher

    async def messages(
        self,
        *,
        email: TeamTextValue,
        phone: TeamTextValue,
        groups: TeamInvitationGroupsPayload,
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
                        "groups": groups,
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
        if isinstance(value, list | Mapping):
            return bool(value)
        return True

    @staticmethod
    def _php_string(value) -> str:
        if value is True:
            return "1"
        if isinstance(value, list | Mapping):
            return "Array"
        return str(value)


class LegacyTeamInvitationLinkBuilder(TeamInvitationLinkBuilder):
    def __init__(self, public_root_url: str) -> None:
        self._root = self._decode_idna_root(public_root_url)

    def build(self, token: str) -> str:
        encoded = quote_plus(token, safe="").replace("~", "%7E")
        return f"{self._root}link.php/{encoded}/"

    @staticmethod
    def _decode_idna_root(public_root_url: str) -> str:
        parts = urlsplit(public_root_url)
        hostname = parts.hostname
        if not hostname:
            return public_root_url.rstrip("/") + "/"
        try:
            decoded_hostname = hostname.encode("ascii").decode("idna")
        except UnicodeError:
            decoded_hostname = hostname
        netloc = parts.netloc.replace(hostname, decoded_hostname, 1)
        return urlunsplit(
            (
                parts.scheme,
                netloc,
                parts.path.rstrip("/") + "/",
                parts.query,
                parts.fragment,
            )
        )


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
