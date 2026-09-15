from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gomazon_webasyst.contracts.enums import (
    AccessReadRejectReason,
    AccessReadResultKind,
    AppAccessKind,
    EffectiveRightKind,
    GroupResolutionKind,
    GroupType,
    RightsSnapshotKind,
    UnlimitedRightReason,
)


class GroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Annotated[str, Field(min_length=1, max_length=255)]
    type: GroupType = GroupType.GROUP
    icon: Annotated[str, Field(max_length=255)] = "user"
    sort: int = 0
    description: str = ""


class GroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Annotated[str, Field(min_length=1, max_length=255)] = ""
    type: GroupType = GroupType.GROUP
    icon: Annotated[str, Field(max_length=255)] = "user"
    sort: int = 0
    description: str = ""

    @model_validator(mode="after")
    def validate_patch(self) -> "GroupUpdate":
        if not self.model_fields_set:
            raise ValueError("group update must contain at least one field")
        return self


class GroupRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Annotated[int, Field(gt=0)]
    name: str
    type: GroupType
    member_count: Annotated[int, Field(ge=0)]
    icon: str
    sort: int
    description: str


class GroupResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[GroupResolutionKind.RESOLVED] = GroupResolutionKind.RESOLVED
    group: GroupRead


class GroupMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[GroupResolutionKind.MISSING] = GroupResolutionKind.MISSING
    group_id: Annotated[int, Field(gt=0)]


GroupResolution: TypeAlias = Annotated[
    GroupResolved | GroupMissing,
    Field(discriminator="kind"),
]


class NoAppAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AppAccessKind.NONE] = AppAccessKind.NONE
    app_id: str


class LimitedAppAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AppAccessKind.LIMITED] = AppAccessKind.LIMITED
    app_id: str


class FullAppAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AppAccessKind.FULL] = AppAccessKind.FULL
    app_id: str


class GlobalAdminAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AppAccessKind.GLOBAL_ADMIN] = AppAccessKind.GLOBAL_ADMIN
    app_id: str


AppAccess: TypeAlias = Annotated[
    NoAppAccess | LimitedAppAccess | FullAppAccess | GlobalAdminAccess,
    Field(discriminator="kind"),
]


class FiniteRight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[EffectiveRightKind.FINITE] = EffectiveRightKind.FINITE
    value: int


class UnlimitedRight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[EffectiveRightKind.UNLIMITED] = EffectiveRightKind.UNLIMITED
    reason: UnlimitedRightReason


EffectiveRight: TypeAlias = Annotated[
    FiniteRight | UnlimitedRight,
    Field(discriminator="kind"),
]


class FiniteRightsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RightsSnapshotKind.FINITE] = RightsSnapshotKind.FINITE
    app_access: AppAccess
    effective_named_rights: dict[str, int]


class UnlimitedRightsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[RightsSnapshotKind.UNLIMITED] = RightsSnapshotKind.UNLIMITED
    app_access: AppAccess
    reason: UnlimitedRightReason


RightsSnapshotResult: TypeAlias = Annotated[
    FiniteRightsSnapshot | UnlimitedRightsSnapshot,
    Field(discriminator="kind"),
]


class AccessReadRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AccessReadResultKind.REJECTED] = AccessReadResultKind.REJECTED
    reason: AccessReadRejectReason


class UserGroupsResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AccessReadResultKind.RESOLVED] = AccessReadResultKind.RESOLVED
    groups: tuple[GroupRead, ...]


UserGroupsResult: TypeAlias = Annotated[
    UserGroupsResolved | AccessReadRejected,
    Field(discriminator="kind"),
]


class GroupMembersResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AccessReadResultKind.RESOLVED] = AccessReadResultKind.RESOLVED
    contact_ids: tuple[int, ...]


GroupMembersResult: TypeAlias = Annotated[
    GroupMembersResolved | AccessReadRejected,
    Field(discriminator="kind"),
]


class EffectiveRightResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AccessReadResultKind.RESOLVED] = AccessReadResultKind.RESOLVED
    right: EffectiveRight


EffectiveRightResult: TypeAlias = Annotated[
    EffectiveRightResolved | AccessReadRejected,
    Field(discriminator="kind"),
]


class AppAccessResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AccessReadResultKind.RESOLVED] = AccessReadResultKind.RESOLVED
    access: AppAccess


AppAccessResult: TypeAlias = Annotated[
    AppAccessResolved | AccessReadRejected,
    Field(discriminator="kind"),
]


class RightsSnapshotResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AccessReadResultKind.RESOLVED] = AccessReadResultKind.RESOLVED
    snapshot: RightsSnapshotResult


RightsSnapshotQueryResult: TypeAlias = Annotated[
    RightsSnapshotResolved | AccessReadRejected,
    Field(discriminator="kind"),
]
