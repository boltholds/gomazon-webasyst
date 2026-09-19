from gomazon_webasyst.application.application_registry import (
    ApplicationCatalog,
    InstallationManifest,
    InstalledApplication,
    StaticApplicationRegistry,
)
from gomazon_webasyst.application.access_control import (
    AssignRight,
    RevokeRight,
    SetAppAccess,
    SetGlobalAdminAccess,
)
from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupTarget,
    GuestsTarget,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_admin_policy import (
    AccessAdministrationAuthorized,
    AccessAdministrationDenied,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectResolved,
)
from gomazon_webasyst.application.ports.rights import (
    NamedRightAssignment,
    RightsPlanApplied,
    RightsSnapshot,
)
from gomazon_webasyst.application.rights_mutation_policy import (
    DeleteAllTargetRights,
    DeleteAppRights,
    DeleteExactRight,
    UpsertAppAccess,
    UpsertGlobalAccess,
    UpsertNamedRight,
)
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import WebasystAccessSemantics
from gomazon_webasyst.compatibility.webasyst.access_control.mutation import LegacyRightsMutationPolicy
from gomazon_webasyst.contracts.applications import ApplicationDescriptor
from gomazon_webasyst.contracts.access_control import (
    AccessMutationRejected,
    AppAccessSet,
    GlobalAdminAccessSet,
    GroupMissing,
    GroupRead,
    GroupResolved,
    RightAlreadyAbsent,
    RightAssigned,
    RightRevoked,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    AccessAdministrationDenyReason,
    AccessMutationRejectReason,
    AppAccessMode,
    GlobalAdminMode,
    GroupType,
)


ACTOR = AuthenticatedSubject(id=1, login="admin")
GROUP = GroupRead(
    id=7,
    name="Operators",
    type=GroupType.GROUP,
    member_count=0,
    icon="user",
    sort=0,
    description="",
)


class FakeAdminPolicy:
    def __init__(self, decision):
        self.decision = decision

    async def authorize(self, actor, uow):
        return self.decision


class FakeSubjects:
    def __init__(self, existing=(42,)):
        self.existing = set(existing)

    async def resolve(self, contact_id):
        if contact_id in self.existing:
            return AccessSubjectResolved(contact_id)
        return AccessSubjectMissing(contact_id)


class FakeGroups:
    def __init__(self, existing=(7,)):
        self.existing = set(existing)

    async def get(self, group_id):
        if group_id.value in self.existing:
            return GroupResolved(group=GROUP)
        return GroupMissing(group_id=group_id.value)


class FakeRights:
    def __init__(self, assignments=()):
        self.snapshot = RightsSnapshot(tuple(assignments))
        self.plans = []

    async def load_for_targets(self, targets):
        return self.snapshot

    async def execute_plan(self, plan):
        self.plans.append(plan)
        return RightsPlanApplied(operation_count=len(plan.operations))


class FakeUow:
    def __init__(self, *, assignments=(), users=(42,), groups=(7,)):
        self.subjects = FakeSubjects(users)
        self.groups = FakeGroups(groups)
        self.rights = FakeRights(assignments)
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def commit(self):
        self.commits += 1


class Factory:
    def __init__(self, uow):
        self.uow = uow

    def __call__(self):
        return self.uow


def mutation_policy():
    return LegacyRightsMutationPolicy(app_semantics=WebasystAccessSemantics())


def authorized():
    return FakeAdminPolicy(AccessAdministrationAuthorized())


def application_registry(
    *,
    enabled: tuple[str, ...] = ("shop", "webasyst"),
    known: tuple[str, ...] = ("shop", "webasyst"),
) -> StaticApplicationRegistry:
    return StaticApplicationRegistry(
        ApplicationCatalog(
            tuple(
                ApplicationDescriptor(id=AppId(app_id), name=app_id.title())
                for app_id in known
            )
        ),
        InstallationManifest(
            tuple(InstalledApplication(AppId(app_id)) for app_id in enabled)
        ),
    )


async def test_denied_actor_never_reaches_rights_store() -> None:
    uow = FakeUow()
    denied = FakeAdminPolicy(
        AccessAdministrationDenied(AccessAdministrationDenyReason.NOT_GLOBAL_ADMIN)
    )

    result = await AssignRight(
        Factory(uow),
        denied,
        mutation_policy(),
        application_registry(),
    )(
        ACTOR,
        UserTarget(42),
        PermissionKey(AppId("shop"), RightName("orders.edit")),
        RightValue(1),
    )

    assert isinstance(result, AccessMutationRejected)
    assert result.reason is AccessMutationRejectReason.ACCESS_DENIED
    assert uow.rights.plans == []
    assert uow.commits == 0


async def test_named_assign_validates_target_and_executes_planner() -> None:
    uow = FakeUow()
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))

    result = await AssignRight(
        Factory(uow),
        authorized(),
        mutation_policy(),
        application_registry(),
    )(
        ACTOR,
        UserTarget(42),
        key,
        RightValue(3),
    )

    assert isinstance(result, RightAssigned)
    assert uow.rights.plans[0].operations == (
        UpsertNamedRight(UserTarget(42), key, RightValue(3)),
    )
    assert uow.commits == 1


async def test_named_assign_rejects_missing_target_reserved_backend_and_zero() -> None:
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))
    missing_uow = FakeUow(users=())

    missing = await AssignRight(
        Factory(missing_uow),
        authorized(),
        mutation_policy(),
        application_registry(),
    )(
        ACTOR,
        UserTarget(42),
        key,
        RightValue(1),
    )
    reserved = await AssignRight(
        Factory(FakeUow()),
        authorized(),
        mutation_policy(),
        application_registry(),
    )(
        ACTOR,
        GuestsTarget(),
        PermissionKey(AppId("shop"), RightName("backend")),
        RightValue(1),
    )
    zero = await AssignRight(
        Factory(FakeUow()),
        authorized(),
        mutation_policy(),
        application_registry(),
    )(
        ACTOR,
        GuestsTarget(),
        key,
        RightValue(0),
    )

    assert isinstance(missing, AccessMutationRejected)
    assert missing.reason is AccessMutationRejectReason.CONTACT_NOT_FOUND
    assert isinstance(reserved, AccessMutationRejected)
    assert reserved.reason is AccessMutationRejectReason.RESERVED_RIGHT
    assert isinstance(zero, AccessMutationRejected)
    assert zero.reason is AccessMutationRejectReason.ZERO_VALUE


async def test_revoke_absent_is_explicit_without_commit() -> None:
    uow = FakeUow()
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))

    result = await RevokeRight(
        Factory(uow),
        authorized(),
        mutation_policy(),
        application_registry(),
    )(
        ACTOR,
        UserTarget(42),
        key,
    )

    assert isinstance(result, RightAlreadyAbsent)
    assert uow.rights.plans == []
    assert uow.commits == 0


async def test_revoke_existing_executes_exact_delete() -> None:
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))
    assignment = NamedRightAssignment(UserTarget(42), key, RightValue(2))
    uow = FakeUow(assignments=(assignment,))

    result = await RevokeRight(
        Factory(uow),
        authorized(),
        mutation_policy(),
        application_registry(),
    )(
        ACTOR,
        UserTarget(42),
        key,
    )

    assert isinstance(result, RightRevoked)
    assert uow.rights.plans[0].operations == (DeleteExactRight(UserTarget(42), key),)
    assert uow.commits == 1


async def test_app_access_modes_use_legacy_cleanup_plans() -> None:
    for mode, expected in (
        (AppAccessMode.LIMITED, (UpsertAppAccess(GroupTarget(GroupId(7)), AppId("shop"), RightValue(1)),)),
        (AppAccessMode.NONE, (DeleteAppRights(GroupTarget(GroupId(7)), AppId("shop")),)),
        (
            AppAccessMode.FULL,
            (
                DeleteAppRights(GroupTarget(GroupId(7)), AppId("shop")),
                UpsertAppAccess(GroupTarget(GroupId(7)), AppId("shop"), RightValue(2)),
            ),
        ),
    ):
        uow = FakeUow()
        result = await SetAppAccess(
            Factory(uow),
            authorized(),
            mutation_policy(),
            application_registry(),
        )(
            ACTOR,
            GroupTarget(GroupId(7)),
            AppId("shop"),
            mode,
        )
        assert isinstance(result, AppAccessSet)
        assert uow.rights.plans[0].operations == expected
        assert uow.commits == 1


async def test_global_control_app_is_rejected_from_set_app_access() -> None:
    uow = FakeUow()

    result = await SetAppAccess(
            Factory(uow),
            authorized(),
            mutation_policy(),
            application_registry(),
        )(
        ACTOR,
        GuestsTarget(),
        AppId("webasyst"),
        AppAccessMode.LIMITED,
    )

    assert isinstance(result, AccessMutationRejected)
    assert result.reason is AccessMutationRejectReason.GLOBAL_CONTROL_APP
    assert uow.commits == 0


async def test_named_assign_rejects_unknown_application_before_planner() -> None:
    uow = FakeUow()
    result = await AssignRight(
        Factory(uow),
        authorized(),
        mutation_policy(),
        application_registry(known=("webasyst",), enabled=("webasyst",)),
    )(
        ACTOR,
        UserTarget(42),
        PermissionKey(AppId("shop"), RightName("orders.edit")),
        RightValue(1),
    )

    assert isinstance(result, AccessMutationRejected)
    assert result.reason is AccessMutationRejectReason.APPLICATION_NOT_FOUND
    assert uow.rights.plans == []
    assert uow.commits == 0


async def test_app_access_rejects_disabled_application_before_planner() -> None:
    uow = FakeUow()
    result = await SetAppAccess(
        Factory(uow),
        authorized(),
        mutation_policy(),
        application_registry(enabled=("webasyst",)),
    )(
        ACTOR,
        UserTarget(42),
        AppId("shop"),
        AppAccessMode.FULL,
    )

    assert isinstance(result, AccessMutationRejected)
    assert result.reason is AccessMutationRejectReason.APPLICATION_DISABLED
    assert uow.rights.plans == []
    assert uow.commits == 0


async def test_revoke_rejects_disabled_application_before_snapshot_lookup() -> None:
    uow = FakeUow()
    result = await RevokeRight(
        Factory(uow),
        authorized(),
        mutation_policy(),
        application_registry(enabled=("webasyst",)),
    )(
        ACTOR,
        UserTarget(42),
        PermissionKey(AppId("shop"), RightName("orders.edit")),
    )

    assert isinstance(result, AccessMutationRejected)
    assert result.reason is AccessMutationRejectReason.APPLICATION_DISABLED
    assert uow.rights.plans == []
    assert uow.commits == 0


async def test_global_admin_enable_and_disable_use_destructive_legacy_plans() -> None:
    for mode, expected in (
        (
            GlobalAdminMode.ENABLED,
            (
                DeleteAllTargetRights(UserTarget(42)),
                UpsertGlobalAccess(UserTarget(42), RightValue(1)),
            ),
        ),
        (GlobalAdminMode.DISABLED, (DeleteAllTargetRights(UserTarget(42)),)),
    ):
        uow = FakeUow()
        result = await SetGlobalAdminAccess(
            Factory(uow), authorized(), mutation_policy()
        )(ACTOR, UserTarget(42), mode)
        assert isinstance(result, GlobalAdminAccessSet)
        assert uow.rights.plans[0].operations == expected
        assert uow.commits == 1
