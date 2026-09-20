from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from gomazon_webasyst.contracts.enums import (
    TeamInvitationChannel,
    TeamInvitationMode,
    TeamInvitationRejectReason,
    TeamInvitationResultKind,
)


class TeamInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: TeamInvitationMode
    email: str = ""
    phone: str = ""
    group_ids: tuple[int, ...] = ()
    send: bool = False


class TeamInvitationPrepared(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contact_id: Annotated[int, Field(gt=0)]
    token: Annotated[str, Field(min_length=1)]
    expires_at: Annotated[int, Field(gt=0)]
    channel: TeamInvitationChannel


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
    | TeamInvitationLocalCodeCreated
    | TeamInvitationWaidCodeCreated
    | TeamInvitationRejected,
    Field(discriminator="kind"),
]
