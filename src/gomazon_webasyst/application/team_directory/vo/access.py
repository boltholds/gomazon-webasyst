from dataclasses import dataclass

from gomazon_webasyst.application.access_values import AppId, GroupId
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamIntState,
)


@dataclass(slots=True, frozen=True)
class TeamUserAppAccess:
    contact_id: int
    app_id: AppId
    value: int

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("Team user app access contact id must be positive")


@dataclass(slots=True, frozen=True)
class TeamGroupManagementRight:
    group_id: GroupId
    value: int


@dataclass(slots=True, frozen=True)
class TeamPrincipalGroupRights:
    principal_contact_id: int
    is_team_admin: bool
    rights: tuple[TeamGroupManagementRight, ...]
    all_groups_fallback: TeamIntState

    def __post_init__(self) -> None:
        if self.principal_contact_id <= 0:
            raise ValueError("Team principal contact id must be positive")
        ids = [right.group_id for right in self.rights]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate Team group management right")
