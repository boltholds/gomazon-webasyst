from datetime import datetime, timezone, tzinfo

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.entities.method_definition import (
    ApiMethodDefinition,
)
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiHttpMethod,
    ApiMethodName,
    ApiMethodTarget,
)
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import ApplicationEventOwner
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.ports.event_publisher import EventPublisher
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
)
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.application.team.groups import ListVisibleTeamGroups
from gomazon_webasyst.application.team.invitation import InviteTeamUser
from gomazon_webasyst.application.team.users import ListVisibleTeamUsers
from gomazon_webasyst.compatibility.webasyst.team.api import (
    TeamGroupsGetListApiMethod,
    TeamUsersGetListApiMethod,
    TeamUsersInviteApiMethod,
)
from gomazon_webasyst.compatibility.webasyst.team.events import (
    TeamContactsDeleteRelayHandler,
)
from gomazon_webasyst.compatibility.webasyst.team.groups_filter import (
    LegacyTeamGroupFilterParser,
)
from gomazon_webasyst.compatibility.webasyst.team.users_filter import (
    LegacyTeamUserFilterParser,
)
from gomazon_webasyst.compatibility.webasyst.team.users_media import (
    LegacyTeamUserMediaProjector,
    RootResourceUrlResolver,
)
from gomazon_webasyst.compatibility.webasyst.team.invitation import (
    DisconnectedTeamWaidInvitationGateway,
    LegacyTeamInvitationHook,
    LegacyTeamInvitationLinkBuilder,
    LegacyTeamInvitationRequestParser,
    LegacyTeamInvitationValidator,
    NoopTeamInvitationEmailSender,
)
from gomazon_webasyst.composition.access_control import create_webasyst_rights_evaluator
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import (
    SQLAlchemyAccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.groups import (
    SQLAlchemyTeamGroupReader,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.users import (
    SQLAlchemyTeamUserReader,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.invitation import (
    SQLAlchemyTeamInvitationStore,
)


_TEAM_APP_ID = AppId("team")


def create_team_runtime_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    event_publisher: EventPublisher,
    installed_applications: InstalledApplicationCatalog,
    public_root_url: str = "http://localhost/",
    server_timezone: tzinfo = timezone.utc,
) -> ApplicationRuntimeModule:
    list_groups = ListVisibleTeamGroups(
        groups=SQLAlchemyTeamGroupReader(session_factory),
        access_uow_factory=SQLAlchemyAccessControlUnitOfWorkFactory(
            session_factory
        ),
        rights_evaluator=create_webasyst_rights_evaluator(),
    )
    groups_handler = TeamGroupsGetListApiMethod(
        list_groups=list_groups,
        filter_parser=LegacyTeamGroupFilterParser(),
    )
    groups_method = ApiMethodDefinition(
        target=ApiMethodTarget(
            _TEAM_APP_ID,
            ApiMethodName("groups.getList"),
        ),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=groups_handler,
    )
    list_users = ListVisibleTeamUsers(
        users=SQLAlchemyTeamUserReader(
            session_factory,
            server_timezone=server_timezone,
            clock=lambda: datetime.now(timezone.utc),
        ),
        access_uow_factory=SQLAlchemyAccessControlUnitOfWorkFactory(
            session_factory
        ),
        rights_evaluator=create_webasyst_rights_evaluator(),
        installed_applications=installed_applications,
    )
    users_handler = TeamUsersGetListApiMethod(
        list_users=list_users,
        filter_parser=LegacyTeamUserFilterParser(),
        media_projector=LegacyTeamUserMediaProjector(
            RootResourceUrlResolver(public_root_url)
        ),
    )
    users_method = ApiMethodDefinition(
        target=ApiMethodTarget(
            _TEAM_APP_ID,
            ApiMethodName("users.getList"),
        ),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=users_handler,
    )
    invite_user = InviteTeamUser(
        store=SQLAlchemyTeamInvitationStore(
            session_factory,
            clock=lambda: datetime.now(server_timezone).replace(tzinfo=None),
        ),
        access_uow_factory=SQLAlchemyAccessControlUnitOfWorkFactory(
            session_factory
        ),
        rights_evaluator=create_webasyst_rights_evaluator(),
        validator=LegacyTeamInvitationValidator(),
        hook=LegacyTeamInvitationHook(event_publisher),
        link_builder=LegacyTeamInvitationLinkBuilder(public_root_url),
        email_sender=NoopTeamInvitationEmailSender(),
        waid=DisconnectedTeamWaidInvitationGateway(),
    )
    invite_handler = TeamUsersInviteApiMethod(
        invite_user=invite_user,
        request_parser=LegacyTeamInvitationRequestParser(),
    )
    invite_method = ApiMethodDefinition(
        target=ApiMethodTarget(
            _TEAM_APP_ID,
            ApiMethodName("users.invite"),
        ),
        allowed_methods=frozenset({ApiHttpMethod("POST")}),
        handler=invite_handler,
    )
    contacts_delete_relay = EventHandlerDefinition(
        handler_id=EventHandlerId("team-contacts-delete-relay"),
        owner=ApplicationEventOwner(_TEAM_APP_ID),
        source=ExactEventSource(AppId("contacts")),
        pattern=ExactEventPattern(EventName("delete")),
        handler=TeamContactsDeleteRelayHandler(event_publisher),
    )
    return ApplicationRuntimeModule(
        app_id=_TEAM_APP_ID,
        dispatch_handlers=(),
        api_methods=(groups_method, users_method, invite_method),
        event_handlers=(contacts_delete_relay,),
        plugins=(),
    )
