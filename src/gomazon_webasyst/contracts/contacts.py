from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

ContactId = Annotated[int, Field(gt=0)]


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=150)]
    firstname: Annotated[str, Field(max_length=50)] = ""
    middlename: Annotated[str, Field(max_length=50)] = ""
    lastname: Annotated[str, Field(max_length=50)] = ""
    title: Annotated[str, Field(max_length=50)] = ""
    company: Annotated[str, Field(max_length=150)] = ""
    jobtitle: Annotated[str, Field(max_length=50)] = ""
    company_contact_id: Annotated[int, Field(ge=0)] = 0
    is_company: bool = False
    locale: Annotated[str, Field(max_length=8)] = ""
    timezone: Annotated[str, Field(max_length=64)] = ""


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=150)] | None = None
    firstname: Annotated[str, Field(max_length=50)] | None = None
    middlename: Annotated[str, Field(max_length=50)] | None = None
    lastname: Annotated[str, Field(max_length=50)] | None = None
    title: Annotated[str, Field(max_length=50)] | None = None
    company: Annotated[str, Field(max_length=150)] | None = None
    jobtitle: Annotated[str, Field(max_length=50)] | None = None
    company_contact_id: Annotated[int, Field(ge=0)] | None = None
    is_company: bool | None = None
    locale: Annotated[str, Field(max_length=8)] | None = None
    timezone: Annotated[str, Field(max_length=64)] | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "ContactUpdate":
        if not self.model_fields_set:
            raise ValueError("contact update must contain at least one field")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("contact profile fields cannot be set to null")
        return self


class ContactRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: ContactId
    name: str
    firstname: str = ""
    middlename: str = ""
    lastname: str = ""
    title: str = ""
    company: str = ""
    jobtitle: str = ""
    company_contact_id: int = 0
    is_company: bool = False
    locale: str = ""
    timezone: str = ""
    create_datetime: datetime
