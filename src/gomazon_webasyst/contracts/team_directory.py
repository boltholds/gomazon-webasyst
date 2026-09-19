from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from gomazon_webasyst.contracts.enums import (
    GroupType,
    TeamCurrentEventKind,
    TeamOnlineStatus,
    TeamValueStateKind,
)


class TeamTextMissingRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamValueStateKind.MISSING] = TeamValueStateKind.MISSING


class TeamTextValueRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamValueStateKind.PRESENT] = TeamValueStateKind.PRESENT
    value: str


TeamTextReadState: TypeAlias = Annotated[
    TeamTextMissingRead | TeamTextValueRead,
    Field(discriminator="kind"),
]


class TeamIntMissingRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamValueStateKind.MISSING] = TeamValueStateKind.MISSING


class TeamIntValueRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamValueStateKind.PRESENT] = TeamValueStateKind.PRESENT
    value: int


TeamIntReadState: TypeAlias = Annotated[
    TeamIntMissingRead | TeamIntValueRead,
    Field(discriminator="kind"),
]


class TeamDateTimeMissingRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamValueStateKind.MISSING] = TeamValueStateKind.MISSING


class TeamDateTimeValueRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamValueStateKind.PRESENT] = TeamValueStateKind.PRESENT
    value: datetime


TeamDateTimeReadState: TypeAlias = Annotated[
    TeamDateTimeMissingRead | TeamDateTimeValueRead,
    Field(discriminator="kind"),
]


class TeamPhoneRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str
    ext: str
    status: TeamTextReadState


class TeamCurrentEventRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    uid: TeamTextReadState
    create_datetime: datetime
    update_datetime: datetime
    contact_id: int
    calendar_id: int
    summary: str
    description: TeamTextReadState
    location: TeamTextReadState
    start: datetime
    end: datetime
    is_allday: bool
    is_status: bool
    sequence: int
    calendar_name: str
    status_bg_color: TeamTextReadState
    status_font_color: TeamTextReadState
    bg_color: TeamTextReadState
    font_color: TeamTextReadState
    icon: TeamTextReadState


class TeamCurrentEventMissingRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamCurrentEventKind.MISSING] = TeamCurrentEventKind.MISSING


class TeamCurrentEventPresentRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[TeamCurrentEventKind.PRESENT] = TeamCurrentEventKind.PRESENT
    event: TeamCurrentEventRead


TeamCurrentEventReadState: TypeAlias = Annotated[
    TeamCurrentEventMissingRead | TeamCurrentEventPresentRead,
    Field(discriminator="kind"),
]


class TeamUserRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    name: str
    firstname: str
    lastname: str
    middlename: str
    company: str
    login: str
    email: tuple[str, ...]
    phone: tuple[TeamPhoneRead, ...]
    locale: str
    jobtitle: str
    last_datetime: TeamDateTimeReadState
    birth_day: TeamIntReadState
    birth_month: TeamIntReadState
    create_datetime: datetime
    userpic: str
    userpic_original_crop: str
    userpic_uploaded: bool
    userpic_thumbs: dict[str, str]
    group_id: tuple[int, ...]
    online_status: TeamOnlineStatus
    current_event: TeamCurrentEventReadState


class TeamGroupRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    name: str
    cnt: int
    type: GroupType
    description: TeamTextReadState


class LegacyTeamPhoneApiRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str
    ext: str
    status: JsonValue


class LegacyTeamUserApiRead(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )

    id: int
    name: str
    firstname: str
    lastname: str
    middlename: str
    company: str
    login: str
    email: tuple[str, ...]
    phone: tuple[LegacyTeamPhoneApiRead, ...]
    locale: str
    jobtitle: str
    last_datetime: JsonValue
    birth_day: JsonValue
    birth_month: JsonValue
    create_datetime: str
    online_status: TeamOnlineStatus = Field(alias="_online_status")
    current_event: JsonValue = Field(alias="_event")
    group_id: tuple[int, ...]
    userpic: str
    userpic_original_crop: str
    userpic_uploaded: bool
    userpic_thumbs: dict[str, str]


class LegacyTeamGroupApiRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    name: str
    cnt: int
    type: GroupType
    description: JsonValue
