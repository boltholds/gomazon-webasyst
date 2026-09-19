from datetime import datetime

import pytest

from gomazon_webasyst.application.access_values import AppId, GroupId
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
from gomazon_webasyst.application.ports.team_current_events import (
    TeamCurrentEventSnapshot,
    TeamUserCurrentEvent,
)
from gomazon_webasyst.application.ports.team_directory import (
    TeamGroupSnapshot,
    TeamUserCandidateSnapshot,
)
from gomazon_webasyst.application.ports.team_memberships import (
    TeamMembershipSnapshot,
)
from gomazon_webasyst.application.ports.team_presence import (
    TeamPresenceSnapshot,
)
from gomazon_webasyst.application.ports.team_user_access import (
    TeamUserAppAccessSnapshot,
)
from gomazon_webasyst.application.team_directory.composites.list_groups import (
    ListTeamGroups,
)
from gomazon_webasyst.application.team_directory.composites.list_users import (
    ListTeamUsers,
)
from gomazon_webasyst.application.team_directory.entities.group import TeamGroup
from gomazon_webasyst.application.team_directory.entities.user_candidate import (
    TeamUserCandidate,
)
from gomazon_webasyst.application.team_directory.vo.access import (
    TeamGroupManagementRight,
    TeamPrincipalGroupRights,
    TeamUserAppAccess,
)
from gomazon_webasyst.application.team_directory.vo.contact import (
    TeamUserMemberships,
)
from gomazon_webasyst.application.team_directory.vo.filters import (
    AllTeamUsers,
    TeamAppAccessRequirement,
    TeamGroupsFilter,
    TeamUsersFilter,
)
from gomazon_webasyst.application.team_directory.vo.presence import (
    TeamOnlineTimeout,
    TeamPresence,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamCurrentEventMissing,
    TeamDateTimeMissing,
    TeamIntMissing,
    TeamIntValue,
    TeamTextMissing,
)
from gomazon_webasyst.contracts.enums import (
    GroupType,
    TeamAccessLevel,
    TeamOnlineStatus,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)


NOW = datetime(2026, 9, 20, 12, 0, 0)


def _candidate(contact_id: int, name: str) -> TeamUserCandidate:
    return TeamUserCandidate(
        id=contact_id,
        name=name,
        firstname=name,
        lastname="",
        middlename="",
        company="",
        login=name.lower(),
        emails=(),
        phones=(),
        locale="en_US",
        jobtitle="",
        last_datetime=TeamDateTimeMissing(),
        birth_day=TeamIntMissing(),
        birth_month=TeamIntMissing(),
        create_datetime=NOW,
        photo_stamp=0,
    )


def _app(app_id: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(app_id.title()),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("example"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


class DirectoryFake:
    def __init__(self) -> None:
        self.user_calls = 0
        self.group_calls = 0
        self.users = (
            _candidate(1, "Principal"),
            _candidate(2, "Hidden"),
            _candidate(3, "Visible"),
        )
        self.groups = (
            TeamGroup(
                GroupId(7),
                "Hidden",
                1,
                GroupType.GROUP,
                TeamTextMissing(),
                1,
            ),
            TeamGroup(
                GroupId(8),
                "Visible",
                1,
                GroupType.LOCATION,
                TeamTextMissing(),
                2,
            ),
        )

    async def list_users(self, scope):
        self.user_calls += 1
        return TeamUserCandidateSnapshot(self.users)

    async def list_groups(self):
        self.group_calls += 1
        return TeamGroupSnapshot(self.groups)


class MembershipFake:
    def __init__(self) -> None:
        self.calls: list[tuple[int, ...]] = []

    async def for_users(self, contact_ids):
        self.calls.append(contact_ids)
        return TeamMembershipSnapshot(
            (
                TeamUserMemberships(1, ()),
                TeamUserMemberships(2, (GroupId(7),)),
                TeamUserMemberships(3, (GroupId(8),)),
            )
        )


class PrincipalRightsFake:
    def __init__(self) -> None:
        self.calls: list[tuple[int, tuple[GroupId, ...]]] = []

    async def read(self, principal_contact_id, group_ids):
        self.calls.append((principal_contact_id, group_ids))
        return TeamPrincipalGroupRights(
            principal_contact_id=principal_contact_id,
            is_team_admin=False,
            rights=(
                TeamGroupManagementRight(GroupId(7), -1),
            ),
            all_groups_fallback=TeamIntValue(1),
        )


class UserAccessFake:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[int, ...], tuple[AppId, ...]]] = []

    async def read(self, contact_ids, app_ids):
        self.calls.append((contact_ids, app_ids))
        return TeamUserAppAccessSnapshot(
            (
                TeamUserAppAccess(1, AppId("crm"), 0),
                TeamUserAppAccess(3, AppId("crm"), 2),
            )
        )


class PresenceFake:
    def __init__(self) -> None:
        self.calls: list[tuple[int, ...]] = []

    async def read(self, contact_ids):
        self.calls.append(contact_ids)
        return TeamPresenceSnapshot(
            tuple(
                TeamPresence(
                    contact_id=contact_id,
                    has_open_login=False,
                    idle_since=TeamDateTimeMissing(),
                )
                for contact_id in contact_ids
            )
        )


class EventsFake:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[int, ...], datetime]] = []

    async def current_for_users(self, contact_ids, now):
        self.calls.append((contact_ids, now))
        return TeamCurrentEventSnapshot(
            tuple(
                TeamUserCurrentEvent(
                    contact_id=contact_id,
                    state=TeamCurrentEventMissing(),
                )
                for contact_id in contact_ids
            )
        )


class ClockFake:
    def now(self):
        return NOW


@pytest.mark.asyncio
async def test_list_team_users_filters_in_batches_and_enriches_only_final_ids() -> None:
    directory = DirectoryFake()
    memberships = MembershipFake()
    rights = PrincipalRightsFake()
    access = UserAccessFake()
    presence = PresenceFake()
    events = EventsFake()
    use_case = ListTeamUsers(
        directory=directory,
        memberships=memberships,
        user_access=access,
        principal_group_rights=rights,
        presence=presence,
        current_events=events,
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("crm"),)
        ),
        clock=ClockFake(),
        online_timeout=TeamOnlineTimeout(300),
    )

    result = await use_case(
        1,
        TeamUsersFilter(
            scope=AllTeamUsers(),
            access=(
                TeamAppAccessRequirement(
                    AppId("crm"),
                    TeamAccessLevel.FULL,
                ),
            ),
        ),
    )

    assert tuple(user.id for user in result.users) == (3,)
    assert result.users[0].online_status is TeamOnlineStatus.OFFLINE
    assert directory.user_calls == 1
    assert memberships.calls == [(1, 2, 3)]
    assert rights.calls == [
        (1, (GroupId(7), GroupId(8)))
    ]
    # Hidden user 2 is removed before access lookup.
    assert access.calls == [
        ((1, 3), (AppId("crm"),))
    ]
    # Only final user 3 is enriched.
    assert presence.calls == [(3,)]
    assert events.calls == [((3,), NOW)]


@pytest.mark.asyncio
async def test_list_team_groups_applies_type_then_legacy_visibility() -> None:
    directory = DirectoryFake()
    rights = PrincipalRightsFake()
    use_case = ListTeamGroups(
        directory=directory,
        principal_group_rights=rights,
    )

    all_groups = await use_case(
        1,
        TeamGroupsFilter(frozenset()),
    )
    locations = await use_case(
        1,
        TeamGroupsFilter(frozenset({GroupType.LOCATION})),
    )

    assert tuple(group.id for group in all_groups.groups) == (
        GroupId(8),
    )
    assert tuple(group.id for group in locations.groups) == (
        GroupId(8),
    )
    assert directory.group_calls == 2
    assert rights.calls[0] == (
        1,
        (GroupId(7), GroupId(8)),
    )
    assert rights.calls[1] == (
        1,
        (GroupId(8),),
    )
