from dataclasses import dataclass

from gomazon_webasyst.application.access_admin_policy import (
    GlobalAdminAccessAdministrationPolicy,
)
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
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.compatibility.webasyst.access_control.mutation import (
    LegacyRightsMutationPolicy,
)
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import (
    SQLAlchemyAccessControlUnitOfWorkFactory,
)


@dataclass(slots=True, frozen=True)
class AccessControlUseCases:
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


def create_access_control_use_cases(session_factory) -> AccessControlUseCases:
    uow_factory = SQLAlchemyAccessControlUnitOfWorkFactory(session_factory)
    app_semantics = WebasystAccessSemantics()
    evaluator = RightsEvaluator(
        app_semantics=app_semantics,
        fallback_policy=ExactThenLegacyAllFallback(),
    )
    mutation_policy = LegacyRightsMutationPolicy(app_semantics=app_semantics)
    admin_policy = GlobalAdminAccessAdministrationPolicy(evaluator=evaluator)

    return AccessControlUseCases(
        get_group=GetGroup(uow_factory),
        list_groups=ListGroups(uow_factory),
        list_user_groups=ListUserGroups(uow_factory),
        list_group_members=ListGroupMembers(uow_factory),
        get_effective_right=GetEffectiveRight(uow_factory, evaluator),
        get_app_access=GetAppAccess(uow_factory, evaluator),
        get_rights_snapshot=GetRightsSnapshot(uow_factory, evaluator),
        create_group=CreateGroup(uow_factory, admin_policy),
        update_group=UpdateGroup(uow_factory, admin_policy),
        delete_group=DeleteGroup(uow_factory, admin_policy),
        add_group_member=AddGroupMember(uow_factory, admin_policy),
        remove_group_member=RemoveGroupMember(uow_factory, admin_policy),
        replace_group_members=ReplaceGroupMembers(uow_factory, admin_policy),
        assign_right=AssignRight(uow_factory, admin_policy, mutation_policy),
        revoke_right=RevokeRight(uow_factory, admin_policy, mutation_policy),
        set_app_access=SetAppAccess(uow_factory, admin_policy, mutation_policy),
        set_global_admin_access=SetGlobalAdminAccess(
            uow_factory,
            admin_policy,
            mutation_policy,
        ),
    )
