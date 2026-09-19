from importlib import import_module

import pytest

from gomazon_webasyst.application.access_values import (
    AppId,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
    AccessSubjectResolved,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    GlobalAccessAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.composition.access_control import create_webasyst_rights_evaluator
from gomazon_webasyst.contracts.auth import AuthenticatedSubject


SUBJECT = AuthenticatedSubject(id=42, login="admin")


def _modules():
    try:
        ports = import_module(
            "gomazon_webasyst.application.ports.oauth_consent_access"
        )
        service = import_module(
            "gomazon_webasyst.compatibility.webasyst.oauth.services.consent_access"
        )
        return ports, service
    except ModuleNotFoundError as error:
        pytest.fail(f"oauth consent access missing: {error}")


class Subjects:
    def __init__(self, result):
        self.result = result

    async def resolve(self, contact_id):
        return self.result


class Memberships:
    async def list_for_user(self, contact_id):
        return ()


class Rights:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def load_for_targets(self, targets):
        return self.snapshot


class Uow:
    def __init__(self, subject_result, snapshot=RightsSnapshot(assignments=())):
        self.subjects = Subjects(subject_result)
        self.memberships = Memberships()
        self.rights = Rights(snapshot)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None


def service(subject_result, snapshot=RightsSnapshot(assignments=())):
    _, module = _modules()
    return module.LegacyOAuthConsentAccessService(
        lambda: Uow(subject_result, snapshot),
        create_webasyst_rights_evaluator(),
    )


@pytest.mark.asyncio
async def test_missing_subject_is_denied() -> None:
    ports, _ = _modules()
    result = await service(AccessSubjectMissing(42)).authorize(
        SUBJECT,
        AppId("shop"),
    )
    assert isinstance(result, ports.OAuthConsentAccessDenied)


@pytest.mark.asyncio
async def test_non_backend_user_is_denied() -> None:
    ports, _ = _modules()
    result = await service(AccessSubjectNotUser(42)).authorize(
        SUBJECT,
        AppId("shop"),
    )
    assert isinstance(result, ports.OAuthConsentAccessDenied)


@pytest.mark.asyncio
async def test_webasyst_without_backend_right_is_denied() -> None:
    ports, _ = _modules()
    result = await service(AccessSubjectResolved(42)).authorize(
        SUBJECT,
        AppId("webasyst"),
    )
    assert isinstance(result, ports.OAuthConsentAccessDenied)


@pytest.mark.asyncio
async def test_regular_app_without_backend_right_is_denied() -> None:
    ports, _ = _modules()
    result = await service(AccessSubjectResolved(42)).authorize(
        SUBJECT,
        AppId("shop"),
    )
    assert isinstance(result, ports.OAuthConsentAccessDenied)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "snapshot",
    [
        RightsSnapshot(
            assignments=(
                AppAccessAssignment(
                    target=UserTarget(42),
                    app_id=AppId("shop"),
                    value=RightValue(1),
                ),
            )
        ),
        RightsSnapshot(
            assignments=(
                AppAccessAssignment(
                    target=UserTarget(42),
                    app_id=AppId("shop"),
                    value=RightValue(2),
                ),
            )
        ),
        RightsSnapshot(
            assignments=(
                GlobalAccessAssignment(
                    target=UserTarget(42),
                    value=RightValue(1),
                ),
            )
        ),
    ],
)
async def test_limited_full_and_global_access_are_granted(snapshot) -> None:
    ports, _ = _modules()
    result = await service(
        AccessSubjectResolved(42),
        snapshot,
    ).authorize(SUBJECT, AppId("shop"))
    assert isinstance(result, ports.OAuthConsentAccessGranted)
