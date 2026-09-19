from importlib import import_module

import pytest

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendLogoutRequest,
)
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.contracts.auth import LogoutResult
from gomazon_webasyst.contracts.backend_session_bridge import (
    BackendLogoutCompleted,
    ClearSessionCredential,
)
from gomazon_webasyst.contracts.enums import LogoutStatus
from gomazon_webasyst.contracts.persistent_login import ClearPersistentCredential


def _flow_class():
    try:
        return import_module(
            "gomazon_webasyst.application.backend_session_bridge.composites.logout"
        ).BackendLogoutFlow
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"logout flow missing: {error}")


class SessionLogout:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, session_id):
        self.calls.append(session_id)
        return self.result


class PersistentRevoke:
    def __init__(self):
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        return ClearPersistentCredential()


@pytest.mark.asyncio
async def test_logout_revokes_runtime_session_and_clears_both_transports() -> None:
    logout = SessionLogout(LogoutResult(status=LogoutStatus.REVOKED))
    persistent = PersistentRevoke()
    flow = _flow_class()(
        logout_backend_session=logout,
        revoke_persistent_credential=persistent,
    )

    result = await flow(
        BackendLogoutRequest(
            session_credential=SessionCredentialProvided(SessionId("sess-1"))
        )
    )

    assert isinstance(result, BackendLogoutCompleted)
    assert result.session_status is LogoutStatus.REVOKED
    assert isinstance(result.session_disposition, ClearSessionCredential)
    assert isinstance(result.persistent_disposition, ClearPersistentCredential)
    assert logout.calls == [SessionId("sess-1")]
    assert persistent.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "credential",
    [SessionCredentialMissing(), SessionCredentialMalformed()],
)
async def test_missing_or_malformed_session_logout_is_idempotent(credential) -> None:
    logout = SessionLogout(LogoutResult(status=LogoutStatus.REVOKED))
    persistent = PersistentRevoke()
    flow = _flow_class()(
        logout_backend_session=logout,
        revoke_persistent_credential=persistent,
    )

    result = await flow(
        BackendLogoutRequest(session_credential=credential)
    )

    assert isinstance(result, BackendLogoutCompleted)
    assert result.session_status is LogoutStatus.ALREADY_MISSING
    assert isinstance(result.session_disposition, ClearSessionCredential)
    assert isinstance(result.persistent_disposition, ClearPersistentCredential)
    assert logout.calls == []
    assert persistent.calls == 1


@pytest.mark.asyncio
async def test_logout_infrastructure_failure_propagates() -> None:
    class BrokenLogout:
        async def __call__(self, session_id):
            raise RuntimeError("session backend down")

    flow = _flow_class()(
        logout_backend_session=BrokenLogout(),
        revoke_persistent_credential=PersistentRevoke(),
    )

    with pytest.raises(RuntimeError, match="session backend down"):
        await flow(
            BackendLogoutRequest(
                session_credential=SessionCredentialProvided(SessionId("sess-1"))
            )
        )
