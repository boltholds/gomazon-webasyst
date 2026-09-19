from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.contracts.enums import GroupType, TeamOnlineStatus


class TeamPhoneRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str
    ext: str
    status: str | None


class TeamCurrentEventRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    uid: str | None
    create_datetime: datetime
    update_datetime: datetime
    contact_id: int
    calendar_id: int
    summary: str
    description: str | None
    location: str | None
    start: datetime
    end: datetime
    is_allday: bool
    is_status: bool
    sequence: int
    calendar_name: str
    status_bg_color: str | None
    status_font_color: str | None
    bg_color: str | None
    font_color: str | None
    icon: str | None


class TeamUserRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

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
    last_datetime: datetime | None
    birth_day: int | None
    birth_month: int | None
    create_datetime: datetime
    userpic: str
    userpic_original_crop: str
    userpic_uploaded: bool
    userpic_thumbs: dict[str, str]
    group_id: tuple[int, ...]
    online_status: TeamOnlineStatus = Field(alias="_online_status")
    current_event: TeamCurrentEventRead | str = Field(alias="_event")


class TeamGroupRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    name: str
    cnt: int
    type: GroupType
    description: str | None
