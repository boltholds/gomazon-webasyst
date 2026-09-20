from gomazon_webasyst.application.access_values import (
    AppId,
    GroupTarget,
    GuestsTarget,
    PermissionKey,
    RightName,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_control_uow import (
    AccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.application.ports.team_invitation import (
    TeamInvitationEmailSender,
    TeamInvitationHook,
    TeamInvitationLinkBuilder,
    TeamInvitationStore,
    TeamInvitationValidator,
    TeamWaidInvitationGateway,
    WaidConnected,
    WaidDisconnected,
    WaidInvitationCodeIssued,
    WaidInvitationCodeRejected,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.contracts.access_control import FiniteRight, UnlimitedRight
from gomazon_webasyst.contracts.enums import (
    TeamInvitationMode,
    TeamInvitationRejectReason,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationContactConflict,
    TeamInvitationLinkCreated,
    TeamInvitationLocalCodeCreated,
    TeamInvitationRejected,
    TeamInvitationRequest,
    TeamInvitationResult,
    TeamInvitationWaidCodeCreated,
)


_TEAM_APP_ID = AppId("team")


_DESCRIPTIONS = {
    TeamInvitationRejectReason.ACCESS_DENIED: "Access denied",
    TeamInvitationRejectReason.GENERAL: "Invitation rejected",
    TeamInvitationRejectReason.EMAIL_REQUIRED: "This is a required field.",
    TeamInvitationRejectReason.EMAIL_INVALID: "This does not look like a valid email address.",
    TeamInvitationRejectReason.PHONE_REQUIRED: "This is a required field.",
    TeamInvitationRejectReason.PHONE_INVALID: "This does not look like a valid phone number.",
    TeamInvitationRejectReason.USER_IN_TEAM: "Already in our team!",
    TeamInvitationRejectReason.CONTACT_BANNED: "This contact was banned.",
    TeamInvitationRejectReason.TOKEN_NOT_CREATED: "Invitation token cannot be created.",
    TeamInvitationRejectReason.EMAIL_SEND_FAIL: "Invitation email cannot be sent.",
}


class InviteTeamUser:
    def __init__(
        self,
        *,
        store: TeamInvitationStore,
        access_uow_factory: AccessControlUnitOfWorkFactory,
        rights_evaluator: RightsEvaluator,
        validator: TeamInvitationValidator,
        hook: TeamInvitationHook,
        link_builder: TeamInvitationLinkBuilder,
        email_sender: TeamInvitationEmailSender,
        waid: TeamWaidInvitationGateway,
    ) -> None:
        self._store = store
        self._access_uow_factory = access_uow_factory
        self._rights_evaluator = rights_evaluator
        self._validator = validator
        self._hook = hook
        self._link_builder = link_builder
        self._email_sender = email_sender
        self._waid = waid

    async def execute(
        self,
        *,
        actor_contact_id: int,
        request: TeamInvitationRequest,
    ) -> TeamInvitationResult:
        snapshot = await self._actor_snapshot(actor_contact_id)
        if not self._php_truthy_right(snapshot, RightName("add_users")):
            return self._reject(TeamInvitationRejectReason.ACCESS_DENIED)

        manageable_groups = tuple(
            group_id
            for group_id in request.group_ids
            if self._php_truthy_right(
                snapshot,
                RightName(f"manage_group.{group_id}"),
            )
        )

        if request.mode is TeamInvitationMode.LINK:
            hook_messages = await self._hook.messages(
                email=request.email,
                phone=request.phone,
                group_ids=request.group_ids,
            )
            if hook_messages:
                return TeamInvitationRejected(
                    reason=TeamInvitationRejectReason.GENERAL,
                    description="\n".join(hook_messages),
                )

            validation = self._link_validation(request)
            if validation:
                return self._reject(validation[0])

        prepared = await self._store.prepare(
            actor_contact_id=actor_contact_id,
            request=request,
            manageable_group_ids=manageable_groups,
        )
        if isinstance(prepared, TeamInvitationContactConflict):
            return TeamInvitationRejected(
                reason=prepared.reason,
                description=_DESCRIPTIONS[prepared.reason],
                details={"contact_id": prepared.contact_id},
            )

        if request.mode is TeamInvitationMode.CODE:
            connection = self._waid.connection()
            if isinstance(connection, WaidDisconnected):
                return TeamInvitationLocalCodeCreated(
                    contact_id=prepared.contact_id
                )
            assert isinstance(connection, WaidConnected)
            code = await self._waid.installation_code(prepared.token)
            if isinstance(code, WaidInvitationCodeRejected):
                await self._store.delete_token(prepared.token)
                details = {
                    "api_error": code.error,
                    "api_description": code.description,
                }
                if code.delay:
                    details["invitation_delay"] = code.delay[0]
                return TeamInvitationRejected(
                    reason=TeamInvitationRejectReason.TOKEN_NOT_CREATED,
                    description=_DESCRIPTIONS[
                        TeamInvitationRejectReason.TOKEN_NOT_CREATED
                    ],
                    details=details,
                )
            assert isinstance(code, WaidInvitationCodeIssued)
            return TeamInvitationWaidCodeCreated(
                contact_id=prepared.contact_id,
                invitation_code=code.code,
                invitation_expire=code.expires_at,
            )

        if request.email and not request.phone and request.send:
            try:
                await self._email_sender.send(
                    prepared,
                    email=request.email,
                    actor_contact_id=actor_contact_id,
                )
            except Exception as exc:
                return TeamInvitationRejected(
                    reason=TeamInvitationRejectReason.EMAIL_SEND_FAIL,
                    description=str(exc),
                    details={"contact_id": prepared.contact_id},
                )

        return TeamInvitationLinkCreated(
            contact_id=prepared.contact_id,
            invitation_link=self._link_builder.build(prepared.token),
            invitation_expire=prepared.expires_at,
        )

    async def _actor_snapshot(self, actor_contact_id: int):
        async with self._access_uow_factory() as uow:
            memberships = await uow.memberships.list_for_user(actor_contact_id)
            targets = (
                UserTarget(actor_contact_id),
                *(GroupTarget(item.group_id) for item in memberships),
                GuestsTarget(),
            )
            return await uow.rights.load_for_targets(targets)

    def _php_truthy_right(self, snapshot, name: RightName) -> bool:
        value = self._rights_evaluator.effective_right(
            snapshot,
            PermissionKey(_TEAM_APP_ID, name),
        )
        if isinstance(value, UnlimitedRight):
            return True
        assert isinstance(value, FiniteRight)
        return value.value != 0

    def _link_validation(
        self,
        request: TeamInvitationRequest,
    ) -> tuple[TeamInvitationRejectReason, ...]:
        if request.phone:
            errors = self._validator.phone_errors(request.phone)
        else:
            errors = self._validator.email_errors(request.email)
        if not errors:
            return ()
        return (TeamInvitationRejectReason(errors[0]),)

    @staticmethod
    def _reject(reason: TeamInvitationRejectReason) -> TeamInvitationRejected:
        return TeamInvitationRejected(
            reason=reason,
            description=_DESCRIPTIONS[reason],
        )
