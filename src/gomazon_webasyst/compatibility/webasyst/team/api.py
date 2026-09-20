from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
)
from gomazon_webasyst.application.api_execution.composites.results import (
    ApiMethodRejected,
    ApiMethodSucceeded,
)
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.api.services.parameter_reader import (
    ApiParameterRejected,
)
from gomazon_webasyst.application.team.groups import ListVisibleTeamGroups
from gomazon_webasyst.application.team.users import ListVisibleTeamUsers
from gomazon_webasyst.application.team.invitation import InviteTeamUser
from gomazon_webasyst.contracts.team import (
    TeamGroupDescriptionMissing,
    TeamGroupDescriptionPresent,
    TeamDateTimeMissing,
    TeamDateTimePresent,
    TeamEventMissing,
    TeamEventPresent,
    TeamGroupRead,
    TeamIntegerMissing,
    TeamIntegerPresent,
    TeamTextMissing,
    TeamTextPresent,
    TeamUserPhone,
    TeamUserRead,
)
from gomazon_webasyst.compatibility.webasyst.team.groups_filter import (
    LegacyTeamGroupFilterParser,
)
from gomazon_webasyst.compatibility.webasyst.team.users_filter import (
    LegacyTeamUserFilterParser,
)
from gomazon_webasyst.compatibility.webasyst.team.users_media import (
    LegacyTeamUserMediaProjector,
)
from gomazon_webasyst.compatibility.webasyst.team.invitation import (
    LegacyTeamInvitationRequestParser,
)
from gomazon_webasyst.contracts.api_execution import (
    ApiApplicationErrorCode,
    ApiMethodError,
)
from gomazon_webasyst.contracts.enums import (
    TeamInvitationRejectReason,
    TeamInvitationResultKind,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationEmailAccepted,
    TeamInvitationLinkCreated,
    TeamInvitationLocalCodeCreated,
    TeamInvitationRejected,
    TeamInvitationWaidCodeCreated,
)


class TeamGroupsGetListApiMethod:
    def __init__(
        self,
        *,
        list_groups: ListVisibleTeamGroups,
        filter_parser: LegacyTeamGroupFilterParser,
    ) -> None:
        self._list_groups = list_groups
        self._filter_parser = filter_parser

    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ) -> ApiMethodSucceeded:
        group_filter = self._filter_parser.parse(parameters)
        groups = await self._list_groups.execute(
            contact_id=context.principal.contact_id,
            group_filter=group_filter,
        )
        return ApiMethodSucceeded(
            payload=[self._legacy_group(group) for group in groups]
        )

    @staticmethod
    def _legacy_group(group: TeamGroupRead) -> dict:
        if isinstance(group.description, TeamGroupDescriptionPresent):
            description = group.description.value
        else:
            assert isinstance(group.description, TeamGroupDescriptionMissing)
            description = None
        return {
            "id": group.id,
            "name": group.name,
            "cnt": group.cnt,
            "type": group.type.value,
            "description": description,
        }


class TeamUsersGetListApiMethod:
    def __init__(
        self,
        *,
        list_users: ListVisibleTeamUsers,
        filter_parser: LegacyTeamUserFilterParser,
        media_projector: LegacyTeamUserMediaProjector,
    ) -> None:
        self._list_users = list_users
        self._filter_parser = filter_parser
        self._media_projector = media_projector

    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ) -> ApiMethodSucceeded:
        user_filter = self._filter_parser.parse(parameters)
        users = await self._list_users.execute(
            contact_id=context.principal.contact_id,
            user_filter=user_filter,
        )
        return ApiMethodSucceeded(
            payload=[self._legacy_user(user) for user in users]
        )

    def _legacy_user(self, user: TeamUserRead) -> dict:
        value = {
            "id": user.id,
            "name": user.name,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "middlename": user.middlename,
            "company": user.company,
            "login": self._text(user.login),
            "email": list(user.email),
            "phone": [self._phone(phone) for phone in user.phone],
            "locale": user.locale,
            "jobtitle": user.jobtitle,
            "last_datetime": self._datetime(user.last_datetime),
            "_event": self._event(user),
            "birth_day": self._integer(user.birth_day),
            "birth_month": self._integer(user.birth_month),
            "create_datetime": user.create_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "_online_status": user.online_status.value,
            "group_id": list(user.group_ids),
        }
        value.update(self._media_projector.project(user))
        return value

    @staticmethod
    def _text(value) -> object:
        if isinstance(value, TeamTextPresent):
            return value.value
        assert isinstance(value, TeamTextMissing)
        return None

    @staticmethod
    def _integer(value) -> object:
        if isinstance(value, TeamIntegerPresent):
            return value.value
        assert isinstance(value, TeamIntegerMissing)
        return None

    @staticmethod
    def _datetime(value) -> object:
        if isinstance(value, TeamDateTimePresent):
            return value.value.strftime("%Y-%m-%d %H:%M:%S")
        assert isinstance(value, TeamDateTimeMissing)
        return None

    @staticmethod
    def _event(user: TeamUserRead) -> object:
        if isinstance(user.event, TeamEventPresent):
            return user.event.value
        assert isinstance(user.event, TeamEventMissing)
        return ""

    @staticmethod
    def _phone(phone: TeamUserPhone) -> dict:
        return {
            "value": phone.value,
            "ext": TeamUsersGetListApiMethod._text(phone.ext),
            "status": TeamUsersGetListApiMethod._text(phone.status),
        }


class TeamUsersInviteApiMethod:
    def __init__(
        self,
        *,
        invite_user: InviteTeamUser,
        request_parser: LegacyTeamInvitationRequestParser,
    ) -> None:
        self._invite_user = invite_user
        self._request_parser = request_parser

    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ):
        request = self._request_parser.parse(parameters)
        if isinstance(request, ApiParameterRejected):
            return ApiMethodRejected(error=request.error)
        result = await self._invite_user.execute(
            actor_contact_id=context.principal.contact_id,
            request=request,
        )
        if isinstance(result, TeamInvitationRejected):
            return ApiMethodRejected(
                error=ApiMethodError(
                    code=ApiApplicationErrorCode(
                        self._error_code(result.reason)
                    ),
                    description=(
                        ""
                        if result.reason
                        is TeamInvitationRejectReason.ACCESS_DENIED
                        else result.description
                    ),
                    http_status=self._status(result.reason),
                    details=result.details,
                )
            )
        if isinstance(result, TeamInvitationLinkCreated):
            return ApiMethodSucceeded(
                payload={
                    "contact_id": result.contact_id,
                    "invitation_link": result.invitation_link,
                    "invitation_expire": result.invitation_expire,
                }
            )
        if isinstance(result, TeamInvitationEmailAccepted):
            return ApiMethodSucceeded(
                payload={
                    "contact_id": result.contact_id,
                    "invitation_expire": result.invitation_expire,
                }
            )
        if isinstance(result, TeamInvitationLocalCodeCreated):
            return ApiMethodSucceeded(
                payload={"contact_id": result.contact_id}
            )
        assert isinstance(result, TeamInvitationWaidCodeCreated)
        return ApiMethodSucceeded(
            payload={
                "contact_id": result.contact_id,
                "invitation_code": result.invitation_code,
                "invitation_expire": result.invitation_expire,
            }
        )

    @staticmethod
    def _status(reason: TeamInvitationRejectReason) -> int:
        if reason is TeamInvitationRejectReason.ACCESS_DENIED:
            return 403
        if reason is TeamInvitationRejectReason.TOKEN_NOT_CREATED:
            return 500
        if reason in {
            TeamInvitationRejectReason.USER_IN_TEAM,
            TeamInvitationRejectReason.CONTACT_BANNED,
        }:
            return 409
        return 400

    @staticmethod
    def _error_code(reason: TeamInvitationRejectReason) -> str:
        if reason is TeamInvitationRejectReason.ACCESS_DENIED:
            return "Access denied"
        return reason.value
