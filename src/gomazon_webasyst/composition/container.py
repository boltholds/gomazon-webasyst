from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from gomazon_webasyst.application.auth import (
    AuthenticateBackendPassword,
    LogoutBackendSession,
    ResolveBackendSession,
)
from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.application.persistent_login import (
    IssuePersistentCredential,
    RestoreBackendSessionFromPersistentCredential,
    RevokePersistentCredential,
)
from gomazon_webasyst.composition.auth import create_auth_use_cases
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.factory import (
    create_engine,
    create_session_factory,
    create_uow_factory,
)


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    get_contact: GetContact
    create_contact: CreateContact
    update_contact: UpdateContact
    authenticate_backend_password: AuthenticateBackendPassword
    resolve_backend_session: ResolveBackendSession
    logout_backend_session: LogoutBackendSession
    issue_persistent_credential: IssuePersistentCredential
    restore_backend_session_from_persistent_credential: RestoreBackendSessionFromPersistentCredential
    revoke_persistent_credential: RevokePersistentCredential

    async def close(self) -> None:
        await self.engine.dispose()


def create_container(settings: Settings) -> Container:
    engine = create_engine(settings)
    uow_factory = create_uow_factory(engine)
    auth = create_auth_use_cases(create_session_factory(engine))
    return Container(
        settings=settings,
        engine=engine,
        get_contact=GetContact(uow_factory),
        create_contact=CreateContact(uow_factory),
        update_contact=UpdateContact(uow_factory),
        authenticate_backend_password=auth.authenticate_backend_password,
        resolve_backend_session=auth.resolve_backend_session,
        logout_backend_session=auth.logout_backend_session,
        issue_persistent_credential=auth.issue_persistent_credential,
        restore_backend_session_from_persistent_credential=(
            auth.restore_backend_session_from_persistent_credential
        ),
        revoke_persistent_credential=auth.revoke_persistent_credential,
    )
