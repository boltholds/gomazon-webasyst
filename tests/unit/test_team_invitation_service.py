import pytest

from gomazon_webasyst.application.access_values import (
    AppId,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    NamedRightAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.application.ports.team_invitation import (
    WaidDisconnected,
    WaidInvitationCodeIssued,
    WaidInvitationCodeRejected,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.application.team.invitation import InviteTeamUser
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.contracts.enums import (
    TeamInvitationChannel,
    TeamInvitationMode,
    TeamInvitationRejectReason,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationLinkCreated,
    TeamInvitationLocalCodeCreated,
    TeamInvitationPrepared,
    TeamInvitationRejected,
    TeamInvitationRequest,
    TeamInvitationWaidCodeCreated,
)


class Memberships:
    async def list_for_user(self, contact_id):
        return ()


class Rights:
    def __init__(self, assignments):
        self.assignments = tuple(assignments)

    async def load_for_targets(self, targets):
        allowed = set(targets)
        return RightsSnapshot(
            tuple(
                item
                for item in self.assignments
                if item.target in allowed
            )
        )


class Uow:
    def __init__(self, rights):
        self.memberships = Memberships()
        self.rights = rights

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class UowFactory:
    def __init__(self, rights):
        self.rights = rights

    def __call__(self):
        return Uow(self.rights)


class Store:
    def __init__(self):
        self.calls = []
        self.deleted = []

    async def prepare(self, *, actor_contact_id, request, manageable_group_ids):
        self.calls.append(
            (actor_contact_id, request, manageable_group_ids)
        )
        return TeamInvitationPrepared(
            contact_id=7,
            token="token",
            expires_at=1_800_000_000,
            channel=(
                TeamInvitationChannel.CODE
                if request.mode is TeamInvitationMode.CODE
                else (
                    TeamInvitationChannel.PHONE
                    if request.phone not in {"", "0"}
                    else TeamInvitationChannel.EMAIL
                )
            ),
        )

    async def delete_token(self, token):
        self.deleted.append(token)


class Validator:
    def __init__(self, email_errors=(), phone_errors=()):
        self._email_errors = email_errors
        self._phone_errors = phone_errors
        self.calls = []

    def email_errors(self, value):
        self.calls.append(("email", value))
        return self._email_errors

    def phone_errors(self, value):
        self.calls.append(("phone", value))
        return self._phone_errors


class Hook:
    def __init__(self, messages=()):
        self._messages = messages
        self.calls = []

    async def messages(self, *, email, phone, group_ids):
        self.calls.append((email, phone, group_ids))
        return self._messages


class LinkBuilder:
    def build(self, token):
        return f"https://example.test/link.php/{token}/"


class EmailSender:
    def __init__(self, error=()):
        self.error = error
        self.calls = []

    async def send(self, invitation, *, email, actor_contact_id):
        self.calls.append((invitation, email, actor_contact_id))
        if self.error:
            raise RuntimeError(self.error[0])


class Waid:
    def __init__(self, *, connected=False, result=()):
        self.connected = connected
        self.result = result
        self.calls = []

    def connection(self):
        if self.connected:
            from gomazon_webasyst.application.ports.team_invitation import (
                WaidConnected,
            )
            return WaidConnected()
        return WaidDisconnected()

    async def installation_code(self, token):
        self.calls.append(token)
        return self.result[0]


def evaluator():
    return RightsEvaluator(
        app_semantics=WebasystAccessSemantics(),
        fallback_policy=ExactThenLegacyAllFallback(),
    )


def service(
    assignments,
    *,
    validator=None,
    hook=None,
    store=None,
    email=None,
    waid=None,
):
    return InviteTeamUser(
        store=store or Store(),
        access_uow_factory=UowFactory(Rights(assignments)),
        rights_evaluator=evaluator(),
        validator=validator or Validator(),
        hook=hook or Hook(),
        link_builder=LinkBuilder(),
        email_sender=email or EmailSender(),
        waid=waid or Waid(),
    )


def limited_actor(*named):
    return (
        AppAccessAssignment(
            UserTarget(42),
            AppId("team"),
            RightValue(1),
        ),
        *named,
    )


@pytest.mark.asyncio
async def test_add_users_zero_denies_before_store() -> None:
    store = Store()
    result = await service(
        limited_actor(),
        store=store,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="a@example.test",
        ),
    )
    assert isinstance(result, TeamInvitationRejected)
    assert result.reason is TeamInvitationRejectReason.ACCESS_DENIED
    assert store.calls == []


@pytest.mark.asyncio
async def test_negative_add_users_is_php_truthy() -> None:
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(-1),
            )
        )
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="a@example.test",
        ),
    )
    assert isinstance(result, TeamInvitationLinkCreated)


@pytest.mark.asyncio
async def test_manage_group_scalar_all_fallback_and_negative_exact_are_truthy() -> None:
    store = Store()
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(1),
            ),
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("manage_group.all")),
                RightValue(1),
            ),
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("manage_group.3")),
                RightValue(-1),
            ),
        ),
        store=store,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="a@example.test",
            group_ids=(2, 3),
        ),
    )
    assert isinstance(result, TeamInvitationLinkCreated)
    assert store.calls[0][2] == (2, 3)


@pytest.mark.asyncio
async def test_hook_rejection_happens_before_email_validation() -> None:
    hook = Hook(("plugin says no",))
    validator = Validator(email_errors=("email_invalid",))
    store = Store()
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(1),
            )
        ),
        hook=hook,
        validator=validator,
        store=store,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="bad",
        ),
    )
    assert isinstance(result, TeamInvitationRejected)
    assert result.reason is TeamInvitationRejectReason.GENERAL
    assert result.description == "plugin says no"
    assert validator.calls == []
    assert store.calls == []


@pytest.mark.asyncio
async def test_phone_priority_hides_email_from_hook() -> None:
    hook = Hook()
    validator = Validator()
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(1),
            )
        ),
        hook=hook,
        validator=validator,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="also@example.test",
            phone="+31 20 123",
        ),
    )
    assert isinstance(result, TeamInvitationLinkCreated)
    assert hook.calls == [("", "+31 20 123", ())]
    assert validator.calls == [("phone", "+31 20 123")]


@pytest.mark.asyncio
async def test_code_flow_skips_hook_and_validation_when_waid_disconnected() -> None:
    hook = Hook(("would reject",))
    validator = Validator(
        email_errors=("email_invalid",),
        phone_errors=("phone_invalid",),
    )
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(1),
            )
        ),
        hook=hook,
        validator=validator,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.CODE,
            email="not-valid",
            phone="also-invalid",
        ),
    )
    assert isinstance(result, TeamInvitationLocalCodeCreated)
    assert hook.calls == []
    assert validator.calls == []


@pytest.mark.asyncio
async def test_connected_waid_code_success_projects_external_code() -> None:
    waid = Waid(
        connected=True,
        result=(WaidInvitationCodeIssued("12345678", 1_800_000_100),),
    )
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(1),
            )
        ),
        waid=waid,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(mode=TeamInvitationMode.CODE),
    )
    assert isinstance(result, TeamInvitationWaidCodeCreated)
    assert result.invitation_code == "12345678"
    assert waid.calls == ["token"]


@pytest.mark.asyncio
async def test_waid_failure_deletes_local_token_and_preserves_details() -> None:
    store = Store()
    waid = Waid(
        connected=True,
        result=(
            WaidInvitationCodeRejected(
                error="rate_limit",
                description="Too many",
                delay=(30,),
            ),
        ),
    )
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(1),
            )
        ),
        store=store,
        waid=waid,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(mode=TeamInvitationMode.CODE),
    )
    assert isinstance(result, TeamInvitationRejected)
    assert result.reason is TeamInvitationRejectReason.TOKEN_NOT_CREATED
    assert result.details == {
        "api_error": "rate_limit",
        "api_description": "Too many",
        "invitation_delay": 30,
    }
    assert store.deleted == ["token"]


@pytest.mark.asyncio
async def test_email_sender_exception_maps_to_email_send_fail() -> None:
    email = EmailSender(error=("template missing",))
    result = await service(
        limited_actor(
            NamedRightAssignment(
                UserTarget(42),
                PermissionKey(AppId("team"), RightName("add_users")),
                RightValue(1),
            )
        ),
        email=email,
    ).execute(
        actor_contact_id=42,
        request=TeamInvitationRequest(
            mode=TeamInvitationMode.LINK,
            email="a@example.test",
            send=True,
        ),
    )
    assert isinstance(result, TeamInvitationRejected)
    assert result.reason is TeamInvitationRejectReason.EMAIL_SEND_FAIL
    assert result.details == {"contact_id": 7}
