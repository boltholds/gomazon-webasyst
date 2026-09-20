from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from gomazon_webasyst.contracts.enums import (
    GroupType,
    TeamGroupDescriptionKind,
    TeamUserAccessLevel,
    TeamUserOnlineStatus,
    TeamValuePresenceKind,
)


class TeamGroupDescriptionPresent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamGroupDescriptionKind.PRESENT] = TeamGroupDescriptionKind.PRESENT
    value: str


class TeamGroupDescriptionMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamGroupDescriptionKind.MISSING] = TeamGroupDescriptionKind.MISSING


TeamGroupDescription: TypeAlias = Annotated[
    TeamGroupDescriptionPresent | TeamGroupDescriptionMissing,
    Field(discriminator="kind"),
]


class TeamGroupRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(gt=0)
    name: str
    cnt: int = Field(ge=0)
    type: GroupType
    description: TeamGroupDescription


class TeamGroupFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    types: tuple[str, ...] = ()


class TeamTextPresent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.PRESENT] = TeamValuePresenceKind.PRESENT
    value: str


class TeamTextMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.MISSING] = TeamValuePresenceKind.MISSING


TeamTextValue: TypeAlias = Annotated[
    TeamTextPresent | TeamTextMissing,
    Field(discriminator="kind"),
]


class TeamIntegerPresent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.PRESENT] = TeamValuePresenceKind.PRESENT
    value: int


class TeamIntegerMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.MISSING] = TeamValuePresenceKind.MISSING


TeamIntegerValue: TypeAlias = Annotated[
    TeamIntegerPresent | TeamIntegerMissing,
    Field(discriminator="kind"),
]


class TeamDateTimePresent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.PRESENT] = TeamValuePresenceKind.PRESENT
    value: datetime


class TeamDateTimeMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.MISSING] = TeamValuePresenceKind.MISSING


TeamDateTimeValue: TypeAlias = Annotated[
    TeamDateTimePresent | TeamDateTimeMissing,
    Field(discriminator="kind"),
]


class TeamEventPresent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.PRESENT] = TeamValuePresenceKind.PRESENT
    value: dict[str, JsonValue]


class TeamEventMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamValuePresenceKind.MISSING] = TeamValuePresenceKind.MISSING


TeamEventValue: TypeAlias = Annotated[
    TeamEventPresent | TeamEventMissing,
    Field(discriminator="kind"),
]


class TeamUserPhone(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str
    ext: TeamTextValue
    status: TeamTextValue


class TeamUserAccessRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    app_id: Annotated[str, Field(min_length=1, max_length=32)]
    level: TeamUserAccessLevel


class TeamUserFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    group_ids: tuple[Annotated[int, Field(gt=0)], ...] = ()
    access: tuple[TeamUserAccessRequirement, ...] = ()


class TeamUserRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Annotated[int, Field(gt=0)]
    name: str
    firstname: str
    lastname: str
    middlename: str
    company: str
    login: TeamTextValue
    email: tuple[str, ...]
    phone: tuple[TeamUserPhone, ...]
    locale: str
    jobtitle: str
    last_datetime: TeamDateTimeValue
    birth_day: TeamIntegerValue
    birth_month: TeamIntegerValue
    create_datetime: datetime
    online_status: TeamUserOnlineStatus
    event: TeamEventValue
    group_ids: tuple[Annotated[int, Field(gt=0)], ...]
    photo_id: Annotated[int, Field(ge=0)]
    is_company: bool
