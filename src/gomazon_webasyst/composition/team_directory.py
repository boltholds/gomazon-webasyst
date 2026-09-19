from dataclasses import dataclass

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
from gomazon_webasyst.application.events.composites.dispatcher import EventDispatcher
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
)
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
    InstalledApplicationMissing,
)
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.application.team_directory.composites.list_groups import (
    ListTeamGroups,
)
from gomazon_webasyst.application.team_directory.composites.list_users import (
    ListTeamUsers,
)
from gomazon_webasyst.application.team_directory.vo.presence import (
    TeamOnlineTimeout,
)
from gomazon_webasyst.compatibility.webasyst.team.api.datetime_policy import (
    LegacyTeamDateTimePolicy,
)
from gomazon_webasyst.compatibility.webasyst.team.api.filters import (
    LegacyTeamApiFilterParser,
)
from gomazon_webasyst.compatibility.webasyst.team.api.methods import (
    TeamGroupsGetListApiMethod,
    TeamUsersGetListApiMethod,
)
from gomazon_webasyst.compatibility.webasyst.team.api.projection import (
    LegacyTeamApiProjector,
)
from gomazon_webasyst.compatibility.webasyst.team.api.resource_urls import (
    LegacyTeamUserResourceUrlPolicy,
)
from gomazon_webasyst.compatibility.webasyst.team.events import (
    TeamContactsCollectionBridge,
)
from gomazon_webasyst.composition.application_runtime import (
    RuntimeModuleFactory,
    RuntimeModuleFactoryBuilder,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.team_directory.clock import SystemTeamClock
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.access import (
    SQLAlchemyTeamPrincipalGroupRightsReader,
    SQLAlchemyTeamUserAppAccessReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.current_events import (
    SQLAlchemyTeamCurrentEventReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.directory import (
    SQLAlchemyTeamDirectoryReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.memberships import (
    SQLAlchemyTeamMembershipReader,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.presence import (
    SQLAlchemyTeamPresenceReader,
)


_TEAM_APP = AppId("team")
_CONTACTS_APP = AppId("contacts")


@dataclass(slots=True, frozen=True)
class TeamRuntimeModuleFactoryBuilder(RuntimeModuleFactoryBuilder):
    settings: Settings

    def create(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> RuntimeModuleFactory:
        return TeamRuntimeModuleFactory(
            session_factory=session_factory,
            settings=self.settings,
        )


@dataclass(slots=True, frozen=True)
class TeamRuntimeModuleFactory(RuntimeModuleFactory):
    session_factory: async_sessionmaker[AsyncSession]
    settings: Settings

    async def build(
        self,
        installed_applications: InstalledApplicationCatalog,
        event_dispatcher: EventDispatcher,
    ) -> tuple[ApplicationRuntimeModule, ...]:
        resolved = await installed_applications.resolve(_TEAM_APP)
        if isinstance(resolved, InstalledApplicationMissing):
            return ()
        return (
            create_team_runtime_module(
                session_factory=self.session_factory,
                installed_applications=installed_applications,
                event_dispatcher=event_dispatcher,
                settings=self.settings,
            ),
        )


def create_team_runtime_module(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    installed_applications: InstalledApplicationCatalog,
    event_dispatcher: EventDispatcher,
    settings: Settings,
) -> ApplicationRuntimeModule:
    directory = SQLAlchemyTeamDirectoryReader(session_factory)
    memberships = SQLAlchemyTeamMembershipReader(session_factory)
    user_access = SQLAlchemyTeamUserAppAccessReader(session_factory)
    principal_rights = SQLAlchemyTeamPrincipalGroupRightsReader(
        session_factory
    )
    presence = SQLAlchemyTeamPresenceReader(session_factory)
    current_events = SQLAlchemyTeamCurrentEventReader(session_factory)

    list_users = ListTeamUsers(
        directory=directory,
        memberships=memberships,
        user_access=user_access,
        principal_group_rights=principal_rights,
        presence=presence,
        current_events=current_events,
        installed_applications=installed_applications,
        clock=SystemTeamClock(),
        online_timeout=TeamOnlineTimeout(300),
    )
    list_groups = ListTeamGroups(
        directory=directory,
        principal_group_rights=principal_rights,
    )

    filters = LegacyTeamApiFilterParser()
    projector = LegacyTeamApiProjector(
        LegacyTeamUserResourceUrlPolicy(
            mod_rewrite=settings.webasyst_mod_rewrite,
        ),
        LegacyTeamDateTimePolicy.from_name(
            settings.webasyst_timezone
        ),
    )

    users_method = ApiMethodDefinition(
        target=ApiMethodTarget(
            _TEAM_APP,
            ApiMethodName("users.getList"),
        ),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=TeamUsersGetListApiMethod(
            list_users=list_users,
            filters=filters,
            projector=projector,
        ),
    )
    groups_method = ApiMethodDefinition(
        target=ApiMethodTarget(
            _TEAM_APP,
            ApiMethodName("groups.getList"),
        ),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=TeamGroupsGetListApiMethod(
            list_groups=list_groups,
            filters=filters,
            projector=projector,
        ),
    )

    event_handler = EventHandlerDefinition(
        handler_id=EventHandlerId(
            "team.contacts.contacts_collection"
        ),
        owner=ApplicationEventOwner(_TEAM_APP),
        source=ExactEventSource(_CONTACTS_APP),
        pattern=ExactEventPattern(
            EventName("contacts_collection")
        ),
        handler=TeamContactsCollectionBridge(event_dispatcher),
    )

    return ApplicationRuntimeModule(
        app_id=_TEAM_APP,
        dispatch_handlers=(),
        api_methods=(users_method, groups_method),
        event_handlers=(event_handler,),
        plugins=(),
    )
