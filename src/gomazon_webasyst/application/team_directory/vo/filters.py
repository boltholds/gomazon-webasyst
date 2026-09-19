from dataclasses import dataclass, field
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId, GroupId
from gomazon_webasyst.contracts.enums import (
    GroupType,
    TeamAccessLevel,
    TeamUserScopeKind,
)


@dataclass(slots=True, frozen=True)
class AllTeamUsers:
    kind: TeamUserScopeKind = field(init=False, default=TeamUserScopeKind.ALL)


@dataclass(slots=True, frozen=True)
class TeamUsersInGroups:
    group_ids: tuple[GroupId, ...]
    kind: TeamUserScopeKind = field(init=False, default=TeamUserScopeKind.GROUPS)

    def __post_init__(self) -> None:
        if not self.group_ids:
            raise ValueError("group-scoped Team users filter requires group ids")
        if len(self.group_ids) != len(set(self.group_ids)):
            raise ValueError("duplicate Team group id")


TeamUserScope: TypeAlias = AllTeamUsers | TeamUsersInGroups


@dataclass(slots=True, frozen=True)
class TeamAppAccessRequirement:
    app_id: AppId
    level: TeamAccessLevel


@dataclass(slots=True, frozen=True)
class TeamUsersFilter:
    scope: TeamUserScope
    access: tuple[TeamAppAccessRequirement, ...]

    def __post_init__(self) -> None:
        app_ids = [item.app_id for item in self.access]
        if len(app_ids) != len(set(app_ids)):
            raise ValueError("duplicate Team access filter application")


@dataclass(slots=True, frozen=True)
class TeamGroupsFilter:
    types: frozenset[GroupType]
