from pydantic import BaseModel, ConfigDict, Field


class TeamGroupRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(gt=0)
    name: str
    cnt: int = Field(ge=0)
    type: str
    description: str | None


class TeamGroupFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    types: tuple[str, ...] = ()
