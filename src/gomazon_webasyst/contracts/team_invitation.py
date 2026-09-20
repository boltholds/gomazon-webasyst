from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from gomazon_webasyst.contracts.enums import (
    TeamInvitationChannel,
    TeamInvitationRejectReason,
    TeamInvitationRequestKind,
    TeamInvitationResultKind,
)
from gomazon_webasyst.contracts.team import (
    TeamTextMissing,
    TeamTextPresent,
    TeamTextValue,
)


class TeamInvitationCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationRequestKind.CODE] = (
        TeamInvitationRequestKind.CODE
    )
    email: TeamTextValue = Field(default_factory=TeamTextMissing)
    phone: TeamTextValue = Field(default_factory=TeamTextMissing)
    requested_groups: tuple[str, ...] = ()
    integer_group_ids: tuple[int, ...] = ()


class TeamInvitationEmailLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationRequestKind.EMAIL_LINK] = (
        TeamInvitationRequestKind.EMAIL_LINK
    )
    email: str
    send: bool = False
    requested_groups: tuple[str, ...] = ()
    integer_group_ids: tuple[int, ...] = ()


class TeamInvitationPhoneLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationRequestKind.PHONE_LINK] = (
        TeamInvitationRequestKind.PHONE_LINK
    )
    phone: str
    requested_groups: tuple[str, ...] = ()
    integer_group_ids: tuple[int, ...] = ()


TeamInvitationRequest: TypeAlias = Annotated[
    TeamInvitationCodeRequest
    | TeamInvitationEmailLinkRequest
    | TeamInvitationPhoneLinkRequest,
    Field(discriminator="kind"),
]


class TeamInvitationPrepared(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contact_id: Annotated[int, Field(gt=0)]
    token: Annotated[str, Field(min_length=1)]
    expires_at: Annotated[int, Field(gt=0)]
    channel: TeamInvitationChannel
    recipient_locale: str


class TeamInvitationContactConflict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: TeamInvitationRejectReason
    contact_id: Annotated[int, Field(gt=0)]


TeamInvitationStoreResult: TypeAlias = (
    TeamInvitationPrepared | TeamInvitationContactConflict
)


class TeamInvitationLinkCreated(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationResultKind.LINK_CREATED] = (
        TeamInvitationResultKind.LINK_CREATED
    )
    contact_id: Annotated[int, Field(gt=0)]
    invitation_link: str
    invitation_expire: Annotated[int, Field(gt=0)]


class TeamInvitationEmailAccepted(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationResultKind.EMAIL_ACCEPTED] = (
        TeamInvitationResultKind.EMAIL_ACCEPTED
    )
    contact_id: Annotated[int, Field(gt=0)]
    invitation_expire: Annotated[int, Field(gt=0)]


class TeamInvitationLocalCodeCreated(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationResultKind.LOCAL_CODE_CREATED] = (
        TeamInvitationResultKind.LOCAL_CODE_CREATED
    )
    contact_id: Annotated[int, Field(gt=0)]


class TeamInvitationWaidCodeCreated(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationResultKind.WAID_CODE_CREATED] = (
        TeamInvitationResultKind.WAID_CODE_CREATED
    )
    contact_id: Annotated[int, Field(gt=0)]
    invitation_code: str
    invitation_expire: Annotated[int, Field(gt=0)]


class TeamInvitationRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[TeamInvitationResultKind.REJECTED] = (
        TeamInvitationResultKind.REJECTED
    )
    reason: TeamInvitationRejectReason
    description: str
    details: dict[str, JsonValue] = Field(default_factory=dict)


TeamInvitationResult: TypeAlias = Annotated[
    TeamInvitationLinkCreated
    | TeamInvitationEmailAccepted
    | TeamInvitationLocalCodeCreated
    | TeamInvitationWaidCodeCreated
    | TeamInvitationRejected,
    Field(discriminator="kind"),
]


def request_email(request: TeamInvitationRequest) -> TeamTextValue:
    if isinstance(request, TeamInvitationEmailLinkRequest):
        return TeamTextPresent(value=request.email)
    if isinstance(request, TeamInvitationCodeRequest):
        return request.email
    assert isinstance(request, TeamInvitationPhoneLinkRequest)
    return TeamTextMissing()


def request_phone(request: TeamInvitationRequest) -> TeamTextValue:
    if isinstance(request, TeamInvitationPhoneLinkRequest):
        return TeamTextPresent(value=request.phone)
    if isinstance(request, TeamInvitationCodeRequest):
        return request.phone
    assert isinstance(request, TeamInvitationEmailLinkRequest)
    return TeamTextMissing()


def request_groups(
    request: TeamInvitationRequest,
) -> tuple[str, ...]:
    return request.requested_groups


def request_integer_groups(
    request: TeamInvitationRequest,
) -> tuple[int, ...]:
    return request.integer_group_ids
