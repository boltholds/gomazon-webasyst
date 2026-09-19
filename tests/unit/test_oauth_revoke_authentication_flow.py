from datetime import datetime, timezone
from importlib import import_module

import pytest

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
)
from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenResolveRejected,
    ApiAccessTokenResolved,
    ApiTokenLastUsedAt,
)
from gomazon_webasyst.contracts.enums import ApiAccessTokenResolveRejectReason


TOKEN = ApiAccessToken("a" * 32)


def _flow():
    try:
        return import_module(
            "gomazon_webasyst.application.oauth_authorization.composites.revoke_authentication"
        )
    except ModuleNotFoundError as error:
        pytest.fail(f"oauth revoke auth flow missing: {error}")


class Resolver:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, token):
        self.calls.append(token)
        return self.result


class Activity:
    def __init__(self):
        self.calls = []

    async def touch_if_due(self, contact_id):
        self.calls.append(contact_id)
        return object()


@pytest.mark.asyncio
async def test_revoke_authentication_sequences_resolve_then_activity() -> None:
    m = _flow()
    activity = Activity()
    resolver = Resolver(
        ApiAccessTokenResolved(
            access_token=TOKEN,
            contact_id=42,
            client_id=ApiClientId("client"),
            scope=ApiScope((AppId("shop"),)),
            last_use=ApiTokenLastUsedAt(
                at=datetime(2026, 9, 19, tzinfo=timezone.utc)
            ),
        )
    )
    result = await m.OAuthRevokeAuthenticationFlow(
        resolve_access_token=resolver,
        activity_service=activity,
    ).authenticate(TOKEN)

    assert isinstance(result, m.OAuthRevokeAuthenticated)
    assert result.contact_id == 42
    assert result.token == TOKEN
    assert resolver.calls == [TOKEN]
    assert activity.calls == [42]


@pytest.mark.asyncio
async def test_rejected_token_short_circuits_activity() -> None:
    m = _flow()
    activity = Activity()
    result = await m.OAuthRevokeAuthenticationFlow(
        resolve_access_token=Resolver(
            ApiAccessTokenResolveRejected(
                reason=ApiAccessTokenResolveRejectReason.MISSING
            )
        ),
        activity_service=activity,
    ).authenticate(TOKEN)

    assert isinstance(result, m.OAuthRevokeAuthenticationRejected)
    assert result.reason is ApiAccessTokenResolveRejectReason.MISSING
    assert activity.calls == []
