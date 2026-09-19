from datetime import datetime
from typing import cast

from pydantic import JsonValue

from gomazon_webasyst.application.api_execution.vo.origin import ApiRequestOrigin
from gomazon_webasyst.application.team_directory.entities.current_event import (
    TeamCurrentEvent,
)
from gomazon_webasyst.application.team_directory.entities.group import TeamGroup
from gomazon_webasyst.application.team_directory.entities.user import TeamUser
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamCurrentEventMissing,
    TeamCurrentEventPresent,
    TeamDateTimeMissing,
    TeamDateTimeValue,
    TeamIntMissing,
    TeamIntValue,
    TeamTextMissing,
    TeamTextValue,
)
from gomazon_webasyst.compatibility.webasyst.team.api.resource_urls import (
    LegacyTeamUserResourceUrlPolicy,
)


class LegacyTeamApiProjector:
    def __init__(
        self,
        resources: LegacyTeamUserResourceUrlPolicy,
    ) -> None:
        self._resources = resources

    def user(
        self,
        user: TeamUser,
        origin: ApiRequestOrigin,
    ) -> dict[str, JsonValue]:
        resources = self._resources.project(user, origin)
        return {
            "id": user.id,
            "name": user.name,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "middlename": user.middlename,
            "company": user.company,
            "login": user.login,
            "email": [item.value for item in user.emails],
            "phone": [
                {
                    "value": item.value,
                    "ext": item.ext,
                    "status": self._text_or_none(item.status),
                }
                for item in user.phones
            ],
            "locale": user.locale,
            "jobtitle": user.jobtitle,
            "last_datetime": self._datetime_or_none(
                user.last_datetime
            ),
            "birth_day": self._int_or_none(user.birth_day),
            "birth_month": self._int_or_none(user.birth_month),
            "create_datetime": self._datetime_string(
                user.create_datetime
            ),
            "_online_status": user.online_status.value,
            "_event": self._event_or_empty(user),
            "group_id": [
                group_id.value for group_id in user.group_ids
            ],
            "userpic": resources.userpic,
            "userpic_original_crop": resources.original_crop,
            "userpic_uploaded": resources.uploaded,
            "userpic_thumbs": resources.thumbs,
        }

    def group(self, group: TeamGroup) -> dict[str, JsonValue]:
        return {
            "id": group.id.value,
            "name": group.name,
            "cnt": group.count,
            "type": group.type.value,
            "description": self._text_or_none(group.description),
        }

    def _event_or_empty(
        self,
        user: TeamUser,
    ) -> JsonValue:
        if isinstance(user.current_event, TeamCurrentEventMissing):
            return ""
        if isinstance(user.current_event, TeamCurrentEventPresent):
            return self._event(user.current_event.event)
        raise AssertionError("unsupported Team current event state")

    def _event(self, event: TeamCurrentEvent) -> dict[str, JsonValue]:
        return {
            "id": event.id,
            "uid": self._text_or_none(event.uid),
            "create_datetime": self._datetime_string(
                event.create_datetime
            ),
            "update_datetime": self._datetime_string(
                event.update_datetime
            ),
            "contact_id": event.contact_id,
            "calendar_id": event.calendar_id,
            "summary": event.summary,
            "description": self._text_or_none(event.description),
            "location": self._text_or_none(event.location),
            "start": self._datetime_string(event.start),
            "end": self._datetime_string(event.end),
            "is_allday": int(event.is_allday),
            "is_status": int(event.is_status),
            "sequence": event.sequence,
            "calendar_name": event.calendar_name,
            "status_bg_color": self._text_or_none(
                event.status_bg_color
            ),
            "status_font_color": self._text_or_none(
                event.status_font_color
            ),
            "bg_color": self._text_or_none(event.bg_color),
            "font_color": self._text_or_none(event.font_color),
            "icon": self._text_or_none(event.icon),
        }

    @staticmethod
    def _text_or_none(state) -> JsonValue:
        if isinstance(state, TeamTextMissing):
            return None
        if isinstance(state, TeamTextValue):
            return state.value
        raise AssertionError("unsupported Team text state")

    @staticmethod
    def _int_or_none(state) -> JsonValue:
        if isinstance(state, TeamIntMissing):
            return None
        if isinstance(state, TeamIntValue):
            return state.value
        raise AssertionError("unsupported Team int state")

    @staticmethod
    def _datetime_or_none(state) -> JsonValue:
        if isinstance(state, TeamDateTimeMissing):
            return None
        if isinstance(state, TeamDateTimeValue):
            return LegacyTeamApiProjector._datetime_string(
                state.value
            )
        raise AssertionError("unsupported Team datetime state")

    @staticmethod
    def _datetime_string(value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")
