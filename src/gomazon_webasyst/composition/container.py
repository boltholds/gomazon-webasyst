from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from gomazon_webasyst.application.access_control import (
    AddGroupMember,
    AssignRight,
    CreateGroup,
    DeleteGroup,
    GetAppAccess,
    GetEffectiveRight,
    GetGroup,
    GetRightsSnapshot,
    ListGroupMembers,
    ListGroups,
    ListUserGroups,
    RemoveGroupMember,
    ReplaceGroupMembers,
    RevokeRight,
    SetAppAccess,
    SetGlobalAdminAccess,
    UpdateGroup,
)
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
from gomazon_webasyst.composition.access_control import create_access_control_use_cases
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
    get_group: GetGroup
    list_groups: ListGroups
    list_user_groups: ListUserGroups
    list_group_members: ListGroupMembers
    get_effective_right: GetEffectiveRight
    get_app_access: GetAppAccess
    get_rights_snapshot: GetRightsSnapshot
    create_group: CreateGroup
    update_group: UpdateGroup
    delete_group: DeleteGroup
    add_group_member: AddGroupMember
    remove_group_member: RemoveGroupMember
    replace_group_members: ReplaceGroupMembers
    assign_right: AssignRight
    revoke_right: RevokeRight
    set_app_access: SetAppAccess
    set_global_admin_access: SetGlobalAdminAccess

    async def close(self) -> None:
        await self.engine.dispose()


def create_container(settings: Settings) -> Container:
    engine = create_engine(settings)
    uow_factory = create_uow_factory(engine)
    session_factory = create_session_factory(engine)
    auth = create_auth_use_cases(session_factory)
    access = create_access_control_use_cases(session_factory)
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
        get_group=access.get_group,
        list_groups=access.list_groups,
        list_user_groups=access.list_user_groups,
        list_group_members=access.list_group_members,
        get_effective_right=access.get_effective_right,
        get_app_access=access.get_app_access,
        get_rights_snapshot=access.get_rights_snapshot,
        create_group=access.create_group,
        update_group=access.update_group,
        delete_group=access.delete_group,
        add_group_member=access.add_group_member,
        remove_group_member=access.remove_group_member,
        replace_group_members=access.replace_group_members,
        assign_right=access.assign_right,
        revoke_right=access.revoke_right,
        set_app_access=access.set_app_access,
        set_global_admin_access=access.set_global_admin_access,
    )