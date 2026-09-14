import pytest

from gomazon_webasyst.application.auth import ResolveBackendSession
from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.ports.session_validation import (
    SessionValidationDecision,
    StrictSessionValidationPolicy,
)
from gomazon_webasyst.contracts.auth import (
    AuthenticatedSubject,
    SessionCreateRequest,
    SessionMetadata,
    SessionResolved,
)
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore


class TrustStoredPolicy:
    def decide(self, state):
        return SessionValidationDecision.TRUST_STORED


class ExplodingSubjectStore:
    async def get(self, subject_id):
        raise AssertionError("subject lookup must be skipped by validation policy")


class ExplodingRegistry:
    async def check(self, key):
        raise AssertionError("registry lookup must be skipped by validation policy")

    async def touch(self, key):
        raise AssertionError("registry touch must be skipped by validation policy")

    async def revoke(self, key):
        raise AssertionError("registry revoke must be skipped by validation policy")


class TokenFactory:
    def create(self, identity):
        return "unused"


def test_strict_policy_explicitly_selects_validation():
    assert StrictSessionValidationPolicy().decide(object()) is SessionValidationDecision.VALIDATE


@pytest.mark.asyncio
async def test_resolve_session_policy_can_trust_stored_state_without_validation_roundtrip():
    store = InMemorySessionStateStore(session_id_factory=lambda: SessionId("sess-1"))
    await store.create(
        SessionCreateRequest(
            subject=AuthenticatedSubject(id=42, login="admin"),
            credential_token="token-v1",
            metadata=SessionMetadata(),
        )
    )
    use_case = ResolveBackendSession(
        session_state=store,
        subject_store=ExplodingSubjectStore(),
        token_factory=TokenFactory(),
        session_registry=ExplodingRegistry(),
        validation_policy=TrustStoredPolicy(),
    )

    result = await use_case(SessionId("sess-1"))

    assert isinstance(result, SessionResolved)
    assert result.session_key == AuthSessionKey(42, SessionId("sess-1"))
    assert result.subject == AuthenticatedSubject(id=42, login="admin")
