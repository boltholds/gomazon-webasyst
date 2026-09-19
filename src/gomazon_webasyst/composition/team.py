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
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.application.team.groups import ListVisibleTeamGroups
from gomazon_webasyst.compatibility.webasyst.team.api import TeamGroupsGetListApiMethod
from gomazon_webasyst.compatibility.webasyst.team.groups_filter import (
    LegacyTeamGroupFilterParser,
)
from gomazon_webasyst.composition.access_control import create_webasyst_rights_evaluator
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import (
    SQLAlchemyAccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.groups import (
    SQLAlchemyTeamGroupReader,
)


_TEAM_APP_ID = AppId("team")


def create_team_runtime_module(
    session_factory: async_sessionmaker[AsyncSession],
) -> ApplicationRuntimeModule:
    list_groups = ListVisibleTeamGroups(
        groups=SQLAlchemyTeamGroupReader(session_factory),
        access_uow_factory=SQLAlchemyAccessControlUnitOfWorkFactory(
            session_factory
        ),
        rights_evaluator=create_webasyst_rights_evaluator(),
    )
    handler = TeamGroupsGetListApiMethod(
        list_groups=list_groups,
        filter_parser=LegacyTeamGroupFilterParser(),
    )
    method = ApiMethodDefinition(
        target=ApiMethodTarget(
            _TEAM_APP_ID,
            ApiMethodName("groups.getList"),
        ),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=handler,
    )
    return ApplicationRuntimeModule(
        app_id=_TEAM_APP_ID,
        dispatch_handlers=(),
        api_methods=(method,),
        event_handlers=(),
        plugins=(),
    )
