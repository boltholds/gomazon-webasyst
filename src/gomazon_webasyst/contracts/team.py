from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.contracts.enums import GroupType, TeamGroupDescriptionKind


class TeamGroupDescriptionPresent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamGroupDescriptionKind.PRESENT] = (
        TeamGroupDescriptionKind.PRESENT
    )
    value: str


class TeamGroupDescriptionMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamGroupDescriptionKind.MISSING] = (
        TeamGroupDescriptionKind.MISSING
    )


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
