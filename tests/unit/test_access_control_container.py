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
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.compatibility.webasyst.access_control.mutation import (
    LegacyRightsMutationPolicy,
)
from gomazon_webasyst.composition.access_control import create_access_control_use_cases
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import (
    SQLAlchemyAccessControlUnitOfWorkFactory,
)


def test_access_control_composition_wires_full_use_case_surface() -> None:
    session_factory = object()

    access = create_access_control_use_cases(session_factory)

    assert isinstance(access.get_group, GetGroup)
    assert isinstance(access.list_groups, ListGroups)
    assert isinstance(access.list_user_groups, ListUserGroups)
    assert isinstance(access.list_group_members, ListGroupMembers)
    assert isinstance(access.get_effective_right, GetEffectiveRight)
    assert isinstance(access.get_app_access, GetAppAccess)
    assert isinstance(access.get_rights_snapshot, GetRightsSnapshot)
    assert isinstance(access.create_group, CreateGroup)
    assert isinstance(access.update_group, UpdateGroup)
    assert isinstance(access.delete_group, DeleteGroup)
    assert isinstance(access.add_group_member, AddGroupMember)
    assert isinstance(access.remove_group_member, RemoveGroupMember)
    assert isinstance(access.replace_group_members, ReplaceGroupMembers)
    assert isinstance(access.assign_right, AssignRight)
    assert isinstance(access.revoke_right, RevokeRight)
    assert isinstance(access.set_app_access, SetAppAccess)
    assert isinstance(access.set_global_admin_access, SetGlobalAdminAccess)


def test_access_control_composition_shares_uow_and_explicit_compatibility_policies() -> None:
    access = create_access_control_use_cases(object())

    uow_factory = access.get_effective_right._uow_factory
    assert isinstance(uow_factory, SQLAlchemyAccessControlUnitOfWorkFactory)
    assert access.create_group._uow_factory is uow_factory
    assert access.assign_right._uow_factory is uow_factory

    evaluator = access.get_effective_right._evaluator
    assert isinstance(evaluator._app_semantics, WebasystAccessSemantics)
    assert isinstance(evaluator._fallback_policy, ExactThenLegacyAllFallback)

    admin_policy = access.create_group._admin_policy
    assert isinstance(admin_policy, GlobalAdminAccessAdministrationPolicy)
    assert admin_policy._evaluator is evaluator

    mutation_policy = access.assign_right._mutation_policy
    assert isinstance(mutation_policy, LegacyRightsMutationPolicy)
    assert access.set_app_access._mutation_policy is mutation_policy
    assert access.set_global_admin_access._mutation_policy is mutation_policy
