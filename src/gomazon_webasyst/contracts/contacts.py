from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gomazon_webasyst.contracts.enums import ContactResolutionKind

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

    name: Annotated[str, Field(min_length=1, max_length=150)] = ""
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

    @model_validator(mode="after")
    def validate_patch(self) -> "ContactUpdate":
        if not self.model_fields_set:
            raise ValueError("contact update must contain at least one field")
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


class ContactResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[ContactResolutionKind.RESOLVED] = ContactResolutionKind.RESOLVED
    contact: ContactRead


class ContactMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[ContactResolutionKind.MISSING] = ContactResolutionKind.MISSING
    contact_id: ContactId


ContactResolution: TypeAlias = Annotated[
    ContactResolved | ContactMissing,
    Field(discriminator="kind"),
]
