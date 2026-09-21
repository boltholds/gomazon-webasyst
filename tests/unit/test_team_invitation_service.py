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
    TeamInvitationEmailRejected,
    TeamInvitationEmailSoftFailure,
    TeamInvitationEmailSent,
    WaidConnected,
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
    TeamInvitationRejectReason,
)
from gomazon_webasyst.contracts.team import TeamTextMissing, TeamTextPresent
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationCodeRequest,
    TeamInvitationEmailAccepted,
    TeamInvitationEmailLinkRequest,
    TeamInvitationLocalCodeCreated,
    TeamInvitationPrepared,
    TeamInvitationRejected,
)


ACTOR = 42


class FakeMemberships:
    async def list_for_user(self, contact_id):
        assert contact_id == ACTOR
        return ()


class FakeRights:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def load_for_targets(self, targets):
        assert targets[0] == UserTarget(ACTOR)
        return self.snapshot


class FakeUow:
    def __init__(self, snapshot):
        self.memberships = FakeMemberships()
        self.rights = FakeRights(snapshot)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeUowFactory:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def __call__(self):
        return FakeUow(self.snapshot)


class FakeStore:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.deleted = []

    async def prepare(
        self,
        *,
        actor_contact_id,
        request,
        manageable_group_ids,
    ):
        self.calls.append(
            (actor_contact_id, request, manageable_group_ids)
        )
        return self.result

    async def delete_token(self, token):
        self.deleted.append(token)


class FakeValidator:
    def __init__(self, *, email=(), phone=()):
        self.email = email
        self.phone = phone

    def email_errors(self, value):
        return self.email

    def phone_errors(self, value):
        return self.phone


class FakeHook:
    def __init__(self, messages=()):
        self.result = messages
        self.calls = []

    async def messages(self, *, email, phone, groups):
        self.calls.append((email, phone, groups))
        return self.result


class FakeLinkBuilder:
    def build(self, token):
        return f"https://example.test/link.php/{token}/"


class FakeEmailSender:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def send(
        self,
        invitation,
        *,
        email,
        actor_contact_id,
    ):
        self.calls.append((invitation, email, actor_contact_id))
        return self.result


class FakeWaid:
    def __init__(self, connection, result=None):
        self._connection = connection
        self._result = result
        self.tokens = []

    def connection(self):
        return self._connection

    async def installation_code(self, token):
        self.tokens.append(token)
        assert self._result is not None
        return self._result


def _snapshot(*, add_users=1, manage_all=0):
    assignments = [
        AppAccessAssignment(
            UserTarget(ACTOR),
            AppId("team"),
            RightValue(1),
        ),
    ]
    if add_users:
        assignments.append(
            NamedRightAssignment(
                UserTarget(ACTOR),
                PermissionKey(
                    AppId("team"),
                    RightName("add_users"),
                ),
                RightValue(add_users),
            )
        )
    if manage_all:
        assignments.append(
            NamedRightAssignment(
                UserTarget(ACTOR),
                PermissionKey(
                    AppId("team"),
                    RightName("manage_group.all"),
                ),
                RightValue(manage_all),
            )
        )
    return RightsSnapshot(tuple(assignments))


def _prepared(channel=TeamInvitationChannel.EMAIL):
    return TeamInvitationPrepared(
        contact_id=7,
        token="token",
        expires_at=1_800_000_000,
        channel=channel,
        recipient_locale="en_US",
    )


def _service(
    *,
    snapshot=None,
    store=None,
    validator=None,
    hook=None,
    sender=None,
    waid=None,
):
    return InviteTeamUser(
        store=store or FakeStore(_prepared()),
        access_uow_factory=FakeUowFactory(
            snapshot or _snapshot()
        ),
        rights_evaluator=RightsEvaluator(
            app_semantics=WebasystAccessSemantics(),
            fallback_policy=ExactThenLegacyAllFallback(),
        ),
        validator=validator or FakeValidator(),
        hook=hook or FakeHook(),
        link_builder=FakeLinkBuilder(),
        email_sender=sender or FakeEmailSender(
            TeamInvitationEmailSent()
        ),
        waid=waid or FakeWaid(WaidDisconnected()),
    )


@pytest.mark.asyncio
async def test_add_users_uses_php_truthiness_and_denies_zero() -> None:
    store = FakeStore(_prepared())
    denied = await _service(
        snapshot=_snapshot(add_users=0),
        store=store,
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationEmailLinkRequest(
            email="a@example.test"
        ),
    )

    assert isinstance(denied, TeamInvitationRejected)
    assert denied.reason is TeamInvitationRejectReason.ACCESS_DENIED
    assert store.calls == []

    allowed_store = FakeStore(_prepared())
    allowed = await _service(
        snapshot=_snapshot(add_users=-1),
        store=allowed_store,
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationEmailLinkRequest(
            email="a@example.test"
        ),
    )

    assert not isinstance(allowed, TeamInvitationRejected)
    assert len(allowed_store.calls) == 1


@pytest.mark.asyncio
async def test_manage_group_scalar_right_uses_dot_all_fallback() -> None:
    store = FakeStore(_prepared())
    result = await _service(
        snapshot=_snapshot(manage_all=-1),
        store=store,
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationEmailLinkRequest(
            email="a@example.test",
            requested_groups=("7", "bad"),
            integer_group_ids=(7,),
        ),
    )

    assert not isinstance(result, TeamInvitationRejected)
    assert store.calls[0][2] == (7,)


@pytest.mark.asyncio
async def test_invite_user_hook_runs_before_channel_validation() -> None:
    hook = FakeHook(("blocked by plugin",))
    store = FakeStore(_prepared())
    result = await _service(
        store=store,
        validator=FakeValidator(email=("email_invalid",)),
        hook=hook,
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationEmailLinkRequest(
            email="not-an-email",
            requested_groups=("bad", "7"),
            integer_group_ids=(7,),
        ),
    )

    assert isinstance(result, TeamInvitationRejected)
    assert result.reason is TeamInvitationRejectReason.GENERAL
    assert result.description == "blocked by plugin"
    assert hook.calls[0][2] == ("bad", "7")
    assert store.calls == []


@pytest.mark.asyncio
async def test_code_flow_skips_hook_and_disconnected_waid_is_local_success() -> None:
    hook = FakeHook(("must not run",))
    store = FakeStore(_prepared(TeamInvitationChannel.CODE))
    result = await _service(
        store=store,
        hook=hook,
        waid=FakeWaid(WaidDisconnected()),
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationCodeRequest(
            email=TeamTextPresent(value="bad"),
            phone=TeamTextMissing(),
        ),
    )

    assert isinstance(result, TeamInvitationLocalCodeCreated)
    assert result.contact_id == 7
    assert hook.calls == []


@pytest.mark.asyncio
async def test_send_true_soft_mail_failure_is_still_success_without_link() -> None:
    sender = FakeEmailSender(
        TeamInvitationEmailSoftFailure()
    )
    result = await _service(sender=sender).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationEmailLinkRequest(
            email="a@example.test",
            send=True,
        ),
    )

    assert isinstance(result, TeamInvitationEmailAccepted)
    assert result.contact_id == 7
    assert len(sender.calls) == 1


@pytest.mark.asyncio
async def test_send_true_hard_mail_failure_preserves_contact_and_token_details() -> None:
    result = await _service(
        sender=FakeEmailSender(
            TeamInvitationEmailRejected("template failed")
        )
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationEmailLinkRequest(
            email="a@example.test",
            send=True,
        ),
    )

    assert isinstance(result, TeamInvitationRejected)
    assert result.reason is TeamInvitationRejectReason.EMAIL_SEND_FAIL
    assert result.description == "template failed"
    assert result.details == {"contact_id": 7}


@pytest.mark.asyncio
async def test_waid_rejection_deletes_local_code_token() -> None:
    store = FakeStore(_prepared(TeamInvitationChannel.CODE))
    waid = FakeWaid(
        WaidConnected(),
        WaidInvitationCodeRejected(
            error="remote_error",
            description="No code",
            delay=(30,),
        ),
    )
    result = await _service(
        store=store,
        waid=waid,
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationCodeRequest(),
    )

    assert isinstance(result, TeamInvitationRejected)
    assert result.reason is TeamInvitationRejectReason.TOKEN_NOT_CREATED
    assert result.details == {
        "api_error": "remote_error",
        "api_description": "No code",
        "invitation_delay": 30,
    }
    assert store.deleted == ["token"]


@pytest.mark.asyncio
async def test_connected_waid_code_success_projects_remote_expiry() -> None:
    result = await _service(
        store=FakeStore(_prepared(TeamInvitationChannel.CODE)),
        waid=FakeWaid(
            WaidConnected(),
            WaidInvitationCodeIssued(
                "12345678",
                1_900_000_000,
            ),
        ),
    ).execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationCodeRequest(),
    )

    assert result.invitation_code == "12345678"
    assert result.invitation_expire == 1_900_000_000
