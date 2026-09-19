from datetime import datetime, timedelta

from gomazon_webasyst.application.access_values import AppId, GroupId
from gomazon_webasyst.application.ports.team_memberships import (
    TeamMembershipSnapshot,
)
from gomazon_webasyst.application.ports.team_user_access import (
    TeamUserAppAccessSnapshot,
)
from gomazon_webasyst.application.team_directory.entities.group import TeamGroup
from gomazon_webasyst.application.team_directory.entities.user_candidate import (
    TeamUserCandidate,
)
from gomazon_webasyst.application.team_directory.services.policies import (
    TeamGroupVisibilityService,
    TeamOnlineStateService,
    TeamUserAccessFilterService,
    TeamUserVisibilityService,
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
    TeamAppAccessRequirement,
)
from gomazon_webasyst.application.team_directory.vo.presence import (
    TeamOnlineTimeout,
    TeamPresence,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamDateTimeMissing,
    TeamDateTimeValue,
    TeamIntMissing,
    TeamIntValue,
)
from gomazon_webasyst.contracts.enums import (
    GroupType,
    TeamAccessLevel,
    TeamOnlineStatus,
)


NOW = datetime(2026, 9, 20, 12, 0, 0)


def user(contact_id: int, name: str) -> TeamUserCandidate:
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
        last_datetime=TeamDateTimeValue(NOW - timedelta(seconds=30)),
        birth_day=TeamIntMissing(),
        birth_month=TeamIntMissing(),
        create_datetime=NOW - timedelta(days=1),
        photo_stamp=0,
    )


def rights(
    *,
    principal: int = 1,
    admin: bool = False,
    values: tuple[tuple[int, int], ...] = (),
    fallback=TeamIntMissing(),
) -> TeamPrincipalGroupRights:
    return TeamPrincipalGroupRights(
        principal_contact_id=principal,
        is_team_admin=admin,
        rights=tuple(
            TeamGroupManagementRight(GroupId(group_id), value)
            for group_id, value in values
        ),
        all_groups_fallback=fallback,
    )


def test_keep_visible_full_team_admin_sees_every_candidate() -> None:
    users = (user(2, "A"), user(3, "B"))
    memberships = TeamMembershipSnapshot(
        (
            TeamUserMemberships(2, (GroupId(7),)),
            TeamUserMemberships(3, (GroupId(9),)),
        )
    )
    assert TeamUserVisibilityService().filter(
        users,
        memberships,
        rights(admin=True, values=((7, -1), (9, -1))),
    ) == users


def test_keep_visible_self_and_groupless_user_are_always_visible() -> None:
    users = (user(1, "Self"), user(2, "NoGroup"))
    memberships = TeamMembershipSnapshot(
        (
            TeamUserMemberships(1, (GroupId(7),)),
            TeamUserMemberships(2, ()),
        )
    )
    assert TeamUserVisibilityService().filter(
        users,
        memberships,
        rights(values=((7, -1),)),
    ) == users


def test_keep_visible_requires_at_least_one_non_hidden_group() -> None:
    users = (user(2, "Hidden"), user(3, "Visible"))
    memberships = TeamMembershipSnapshot(
        (
            TeamUserMemberships(2, (GroupId(7), GroupId(8))),
            TeamUserMemberships(3, (GroupId(7), GroupId(9))),
        )
    )
    visible = TeamUserVisibilityService().filter(
        users,
        memberships,
        rights(values=((7, -1), (8, -1), (9, 0))),
    )
    assert tuple(item.id for item in visible) == (3,)


def test_keep_visible_does_not_apply_all_fallback_to_target_group_ids() -> None:
    target = user(2, "Target")
    memberships = TeamMembershipSnapshot(
        (TeamUserMemberships(2, (GroupId(7),)),)
    )
    visible = TeamUserVisibilityService().filter(
        (target,),
        memberships,
        rights(fallback=TeamIntValue(-1)),
    )
    assert visible == (target,)


def test_user_access_filter_requires_every_app_and_distinguishes_limited_full() -> None:
    users = (user(2, "Two"), user(3, "Three"))
    requirements = (
        TeamAppAccessRequirement(AppId("crm"), TeamAccessLevel.LIMITED),
        TeamAppAccessRequirement(AppId("files"), TeamAccessLevel.FULL),
    )
    snapshot = TeamUserAppAccessSnapshot(
        (
            TeamUserAppAccess(2, AppId("crm"), 1),
            TeamUserAppAccess(2, AppId("files"), 2),
            TeamUserAppAccess(3, AppId("crm"), 2),
            TeamUserAppAccess(3, AppId("files"), 1),
        )
    )
    assert TeamUserAccessFilterService().filter(
        users,
        requirements,
        snapshot,
    ) == (users[0],)


def test_group_visibility_uses_exact_right_then_all_fallback() -> None:
    groups = (
        TeamGroup(GroupId(7), "Seven", 1, GroupType.GROUP, __import__(
            "gomazon_webasyst.application.team_directory.vo.states",
            fromlist=["TeamTextMissing"],
        ).TeamTextMissing(), 1),
        TeamGroup(GroupId(8), "Eight", 1, GroupType.GROUP, __import__(
            "gomazon_webasyst.application.team_directory.vo.states",
            fromlist=["TeamTextMissing"],
        ).TeamTextMissing(), 2),
    )
    visible = TeamGroupVisibilityService().filter(
        groups,
        rights(
            values=((7, -1),),
            fallback=TeamIntValue(1),
        ),
    )
    assert visible == (groups[1],)


def test_group_visibility_zero_exact_falls_back_like_legacy_get_rights() -> None:
    from gomazon_webasyst.application.team_directory.vo.states import TeamTextMissing

    group = TeamGroup(
        GroupId(7), "Seven", 1, GroupType.GROUP, TeamTextMissing(), 1
    )
    assert TeamGroupVisibilityService().filter(
        (group,),
        rights(values=((7, 0),), fallback=TeamIntValue(-1)),
    ) == ()


def test_online_state_offline_online_and_idle() -> None:
    service = TeamOnlineStateService()
    timeout = TeamOnlineTimeout(300)

    offline = service.resolve(
        last_datetime=TeamDateTimeMissing(),
        presence=TeamPresence(1, False, TeamDateTimeMissing()),
        now=NOW,
        timeout=timeout,
    )
    online = service.resolve(
        last_datetime=TeamDateTimeValue(NOW - timedelta(seconds=299)),
        presence=TeamPresence(1, False, TeamDateTimeMissing()),
        now=NOW,
        timeout=timeout,
    )
    idle = service.resolve(
        last_datetime=TeamDateTimeValue(NOW - timedelta(seconds=30)),
        presence=TeamPresence(
            1,
            True,
            TeamDateTimeValue(NOW - timedelta(seconds=61)),
        ),
        now=NOW,
        timeout=timeout,
    )

    assert offline is TeamOnlineStatus.OFFLINE
    assert online is TeamOnlineStatus.ONLINE
    assert idle is TeamOnlineStatus.IDLE


def test_stale_idle_setting_without_open_login_does_not_mark_idle() -> None:
    status = TeamOnlineStateService().resolve(
        last_datetime=TeamDateTimeValue(NOW - timedelta(seconds=30)),
        presence=TeamPresence(
            1,
            False,
            TeamDateTimeValue(NOW - timedelta(hours=1)),
        ),
        now=NOW,
        timeout=TeamOnlineTimeout(300),
    )
    assert status is TeamOnlineStatus.ONLINE
