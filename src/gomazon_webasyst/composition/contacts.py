from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.contacts_app.delete_rights import (
    DeleteContactsPrivateRights,
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
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.compatibility.webasyst.contacts.events import (
    ContactsDeletePrivateRightsHandler,
)
from gomazon_webasyst.infrastructure.contacts_app.sqlalchemy.rights import (
    SQLAlchemyContactsPrivateRightsCleaner,
)


_CONTACTS_APP_ID = AppId("contacts")


def create_contacts_runtime_module(
    session_factory: async_sessionmaker[AsyncSession],
) -> ApplicationRuntimeModule:
    delete_rights = DeleteContactsPrivateRights(
        SQLAlchemyContactsPrivateRightsCleaner(session_factory)
    )
    private_rights_delete = EventHandlerDefinition(
        handler_id=EventHandlerId("contacts-private-rights-delete"),
        owner=ApplicationEventOwner(_CONTACTS_APP_ID),
        source=ExactEventSource(_CONTACTS_APP_ID),
        pattern=ExactEventPattern(EventName("delete")),
        handler=ContactsDeletePrivateRightsHandler(delete_rights),
    )
    return ApplicationRuntimeModule(
        app_id=_CONTACTS_APP_ID,
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(private_rights_delete,),
        plugins=(),
    )
