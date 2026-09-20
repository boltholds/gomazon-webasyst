from datetime import datetime

import pytest

from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupMembership,
    GroupTarget,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
    GuestsTarget,
)
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilities,
)
from gomazon_webasyst.application.application_registry.vo.header_items import (
    ApplicationHeaderItems,
)
from gomazon_webasyst.application.application_registry.vo.icons import (
    ApplicationIconSet,
)
from gomazon_webasyst.application.application_registry.vo.metadata import (
    ApplicationDisplayName,
    ApplicationVendor,
    ApplicationVersion,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    NamedRightAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.application.team.users import ListVisibleTeamUsers
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.contracts.enums import (
    TeamUserAccessLevel,
    TeamUserOnlineStatus,
)
from gomazon_webasyst.contracts.team import (
    TeamDateTimeMissing,
    TeamEventMissing,
    TeamIntegerMissing,
    TeamTextMissing,
    TeamUserAccessRequirement,
    TeamUserFilter,
    TeamUserRead,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)


def _user(user_id: int, groups: tuple[int, ...] = ()) -> TeamUserRead:
    return TeamUserRead(
        id=user_id,
        name=f"User {user_id}",
        firstname="",
        lastname="",
        middlename="",
        company="",
        login=TeamTextMissing(),
        email=(),
        phone=(),
        locale="",
        jobtitle="",
        last_datetime=TeamDateTimeMissing(),
        birth_day=TeamIntegerMissing(),
        birth_month=TeamIntegerMissing(),
        create_datetime=datetime(2026, 9, 20, 12, 0, 0),
        online_status=TeamUserOnlineStatus.OFFLINE,
        event=TeamEventMissing(),
        group_ids=groups,
        photo_id=0,
        is_company=False,
    )


def _app(app_id: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(app_id.title()),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("test"),
        version=ApplicationVersion("1.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


class FakeReader:
    def __init__(self, users: tuple[TeamUserRead, ...]) -> None:
        self.users = users
        self.group_calls: list[tuple[int, ...]] = []

    async def list_candidates(self, group_ids: tuple[int, ...]):
        self.group_calls.append(group_ids)
        return self.users


class FakeMemberships:
    def __init__(self, actor_groups: tuple[int, ...]) -> None:
        self.actor_groups = actor_groups

    async def list_for_user(self, contact_id: int):
        return tuple(
            GroupMembership(contact_id, GroupId(group_id))
            for group_id in self.actor_groups
        )


class FilteringRights:
    def __init__(self, assignments) -> None:
        self.assignments = tuple(assignments)
        self.calls = []

    async def load_for_targets(self, targets):
        self.calls.append(targets)
        target_set = set(targets)
        return RightsSnapshot(
            tuple(
                assignment
                for assignment in self.assignments
                if assignment.target in target_set
            )
        )


class FakeUow:
    def __init__(self, memberships, rights) -> None:
        self.memberships = memberships
        self.rights = rights

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeUowFactory:
    def __init__(self, uow) -> None:
        self.uow = uow

    def __call__(self):
        return self.uow


def _evaluator() -> RightsEvaluator:
    return RightsEvaluator(
        app_semantics=WebasystAccessSemantics(),
        fallback_policy=ExactThenLegacyAllFallback(),
    )


@pytest.mark.asyncio
async def test_non_admin_visibility_keeps_self_ungrouped_and_any_visible_group() -> None:
    actor_id = 100
    reader = FakeReader(
        (
            _user(actor_id, (2,)),
            _user(1),
            _user(2, (2, 3)),
            _user(3, (2,)),
        )
    )
    rights = FilteringRights(
        (
            AppAccessAssignment(
                UserTarget(actor_id),
                AppId("team"),
                RightValue(1),
            ),
            NamedRightAssignment(
                UserTarget(actor_id),
                PermissionKey(
                    AppId("team"),
                    RightName("manage_users_in_group.2"),
                ),
                RightValue(-1),
            ),
        )
    )
    service = ListVisibleTeamUsers(
        users=reader,
        access_uow_factory=FakeUowFactory(
            FakeUow(FakeMemberships(()), rights)
        ),
        rights_evaluator=_evaluator(),
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("team"),)
        ),
    )

    result = await service.execute(
        contact_id=actor_id,
        user_filter=TeamUserFilter(group_ids=(2,)),
    )

    assert [user.id for user in result] == [100, 1, 2]
    assert reader.group_calls == [(2,)]


@pytest.mark.asyncio
async def test_team_admin_bypasses_hidden_group_visibility() -> None:
    actor_id = 100
    reader = FakeReader((_user(1, (2,)), _user(2, (3,))))
    rights = FilteringRights(
        (
            AppAccessAssignment(
                UserTarget(actor_id),
                AppId("team"),
                RightValue(2),
            ),
            NamedRightAssignment(
                UserTarget(actor_id),
                PermissionKey(
                    AppId("team"),
                    RightName("manage_users_in_group.2"),
                ),
                RightValue(-1),
            ),
        )
    )
    service = ListVisibleTeamUsers(
        users=reader,
        access_uow_factory=FakeUowFactory(
            FakeUow(FakeMemberships(()), rights)
        ),
        rights_evaluator=_evaluator(),
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("team"),)
        ),
    )

    result = await service.execute(
        contact_id=actor_id,
        user_filter=TeamUserFilter(),
    )

    assert [user.id for user in result] == [1, 2]


@pytest.mark.asyncio
async def test_access_filter_is_and_and_does_not_use_guest_principal() -> None:
    actor_id = 100
    reader = FakeReader((_user(1, (10,)), _user(2)))
    rights = FilteringRights(
        (
            AppAccessAssignment(
                UserTarget(actor_id),
                AppId("team"),
                RightValue(2),
            ),
            AppAccessAssignment(
                UserTarget(1),
                AppId("crm"),
                RightValue(1),
            ),
            AppAccessAssignment(
                GroupTarget(GroupId(10)),
                AppId("files"),
                RightValue(2),
            ),
            AppAccessAssignment(
                GuestsTarget(),
                AppId("crm"),
                RightValue(2),
            ),
            AppAccessAssignment(
                GuestsTarget(),
                AppId("files"),
                RightValue(2),
            ),
        )
    )
    service = ListVisibleTeamUsers(
        users=reader,
        access_uow_factory=FakeUowFactory(
            FakeUow(FakeMemberships(()), rights)
        ),
        rights_evaluator=_evaluator(),
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("team"), _app("crm"), _app("files"))
        ),
    )

    result = await service.execute(
        contact_id=actor_id,
        user_filter=TeamUserFilter(
            access=(
                TeamUserAccessRequirement(
                    app_id="crm",
                    level=TeamUserAccessLevel.LIMITED,
                ),
                TeamUserAccessRequirement(
                    app_id="files",
                    level=TeamUserAccessLevel.FULL,
                ),
            )
        ),
    )

    assert [user.id for user in result] == [1]
    candidate_two_call = next(
        call
        for call in rights.calls
        if call and call[0] == UserTarget(2)
    )
    assert GuestsTarget() not in candidate_two_call


@pytest.mark.asyncio
async def test_uninstalled_access_filter_app_returns_empty_list() -> None:
    actor_id = 100
    reader = FakeReader((_user(1),))
    rights = FilteringRights(
        (
            AppAccessAssignment(
                UserTarget(actor_id),
                AppId("team"),
                RightValue(2),
            ),
        )
    )
    service = ListVisibleTeamUsers(
        users=reader,
        access_uow_factory=FakeUowFactory(
            FakeUow(FakeMemberships(()), rights)
        ),
        rights_evaluator=_evaluator(),
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("team"),)
        ),
    )

    result = await service.execute(
        contact_id=actor_id,
        user_filter=TeamUserFilter(
            access=(
                TeamUserAccessRequirement(
                    app_id="missing",
                    level=TeamUserAccessLevel.LIMITED,
                ),
            )
        ),
    )

    assert result == ()
    assert len(rights.calls) == 0
