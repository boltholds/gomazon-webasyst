import pytest

from gomazon_webasyst.application.access_values import (
    AppId,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.application.ports.memberships import MembershipRepository
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    NamedRightAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.application.team.groups import ListVisibleTeamGroups
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.contracts.team import (
    TeamGroupDescriptionMissing,
    TeamGroupDescriptionPresent,
    TeamGroupFilter,
    TeamGroupRead,
)


class FakeGroups:
    def __init__(self, groups: tuple[TeamGroupRead, ...]) -> None:
        self.groups = groups

    async def list_ordered_by_sort(self) -> tuple[TeamGroupRead, ...]:
        return self.groups


class EmptyMemberships:
    async def list_for_user(self, contact_id: int):
        return ()


class FixedRights:
    def __init__(self, snapshot: RightsSnapshot) -> None:
        self.snapshot = snapshot
        self.targets = ()

    async def load_for_targets(self, targets):
        self.targets = targets
        return self.snapshot


class FakeUow:
    def __init__(self, snapshot: RightsSnapshot) -> None:
        self.memberships = EmptyMemberships()
        self.rights = FixedRights(snapshot)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None


class FakeUowFactory:
    def __init__(self, snapshot: RightsSnapshot) -> None:
        self.snapshot = snapshot
        self.created: list[FakeUow] = []

    def __call__(self):
        uow = FakeUow(self.snapshot)
        self.created.append(uow)
        return uow


def _groups() -> tuple[TeamGroupRead, ...]:
    return (
        TeamGroupRead(id=2, name="Office", cnt=2, type="location", description=TeamGroupDescriptionMissing()),
        TeamGroupRead(id=1, name="Engineering", cnt=5, type="group", description=TeamGroupDescriptionPresent(value="Eng")),
        TeamGroupRead(id=3, name="QA", cnt=3, type="group", description=TeamGroupDescriptionMissing()),
    )


def _service(snapshot: RightsSnapshot) -> ListVisibleTeamGroups:
    return ListVisibleTeamGroups(
        groups=FakeGroups(_groups()),
        access_uow_factory=FakeUowFactory(snapshot),
        rights_evaluator=RightsEvaluator(
            app_semantics=WebasystAccessSemantics(),
            fallback_policy=ExactThenLegacyAllFallback(),
        ),
    )


@pytest.mark.asyncio
async def test_limited_access_hides_only_group_with_negative_exact_right() -> None:
    subject = UserTarget(42)
    snapshot = RightsSnapshot(
        (
            AppAccessAssignment(subject, AppId("team"), RightValue(1)),
            NamedRightAssignment(
                subject,
                PermissionKey(
                    AppId("team"),
                    RightName("manage_users_in_group.1"),
                ),
                RightValue(-1),
            ),
        )
    )

    groups = await _service(snapshot).execute(
        contact_id=42,
        group_filter=TeamGroupFilter(),
    )

    assert tuple(group.id for group in groups) == (2, 3)


@pytest.mark.asyncio
async def test_legacy_all_right_is_fallback_for_zero_or_missing_exact_right() -> None:
    subject = UserTarget(42)
    snapshot = RightsSnapshot(
        (
            AppAccessAssignment(subject, AppId("team"), RightValue(1)),
            NamedRightAssignment(
                subject,
                PermissionKey(
                    AppId("team"),
                    RightName("manage_users_in_group.all"),
                ),
                RightValue(-1),
            ),
            NamedRightAssignment(
                subject,
                PermissionKey(
                    AppId("team"),
                    RightName("manage_users_in_group.3"),
                ),
                RightValue(1),
            ),
        )
    )

    groups = await _service(snapshot).execute(
        contact_id=42,
        group_filter=TeamGroupFilter(),
    )

    assert tuple(group.id for group in groups) == (3,)


@pytest.mark.asyncio
async def test_full_team_access_makes_group_rights_unlimited() -> None:
    subject = UserTarget(42)
    snapshot = RightsSnapshot(
        (
            AppAccessAssignment(subject, AppId("team"), RightValue(2)),
            NamedRightAssignment(
                subject,
                PermissionKey(
                    AppId("team"),
                    RightName("manage_users_in_group.1"),
                ),
                RightValue(-1),
            ),
        )
    )

    groups = await _service(snapshot).execute(
        contact_id=42,
        group_filter=TeamGroupFilter(),
    )

    assert tuple(group.id for group in groups) == (2, 1, 3)


@pytest.mark.asyncio
async def test_type_filter_is_applied_before_visibility_projection() -> None:
    subject = UserTarget(42)
    snapshot = RightsSnapshot(
        (AppAccessAssignment(subject, AppId("team"), RightValue(1)),)
    )

    groups = await _service(snapshot).execute(
        contact_id=42,
        group_filter=TeamGroupFilter(types=("group",)),
    )

    assert tuple(group.id for group in groups) == (1, 3)
