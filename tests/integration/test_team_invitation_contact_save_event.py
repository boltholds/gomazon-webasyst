from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
)
from gomazon_webasyst.application.events.vo.contacts import (
    ContactsSaveEventPayload,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.application.team.invitation import InviteTeamUser
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.compatibility.webasyst.team.invitation import (
    DisconnectedTeamWaidInvitationGateway,
    LegacyTeamInvitationLinkBuilder,
    LegacyTeamInvitationValidator,
    UnavailableTeamInvitationEmailSender,
)
from gomazon_webasyst.contracts.team import TeamTextPresent
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationCodeRequest,
    TeamInvitationLocalCodeCreated,
)
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import (
    SQLAlchemyAccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactRightRow,
    WaContactRow,
)
from gomazon_webasyst.infrastructure.team.sqlalchemy.invitation import (
    SQLAlchemyTeamInvitationStore,
)


NOW = datetime(2026, 9, 20, 12, 0, 0)
ACTOR = 42


class NoopInvitationHook:
    async def messages(self, *, email, phone, groups):
        del email, phone, groups
        raise AssertionError("code invitation must not publish team.invite_user")


class InspectingContactsSavePublisher:
    def __init__(self, sessions) -> None:
        self._sessions = sessions
        self.contact_ids: list[int] = []

    async def publish(self, request):
        assert request.event.app_id == AppId("contacts")
        assert request.event.name.value == "save"
        assert isinstance(request.payload, ContactsSaveEventPayload)
        contact_id = request.payload.contact_id

        async with self._sessions() as session:
            contact = await session.get(WaContactRow, contact_id)
            assert contact is not None
            email = (
                await session.execute(
                    text(
                        "SELECT email FROM wa_contact_emails "
                        "WHERE contact_id=:contact_id"
                    ),
                    {"contact_id": contact_id},
                )
            ).scalar_one()
            token_count = (
                await session.execute(
                    text(
                        "SELECT COUNT(*) FROM wa_app_tokens "
                        "WHERE contact_id=:contact_id"
                    ),
                    {"contact_id": contact_id},
                )
            ).scalar_one()

        assert email == "new@example.test"
        assert token_count == 0
        self.contact_ids.append(contact_id)
        return EventDispatchReport(
            event=request.event,
            results=(),
            failures=(),
        )


@pytest.mark.asyncio
async def test_new_invite_contact_is_committed_and_saved_event_runs_before_token() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.exec_driver_sql(
            "CREATE TABLE wa_app_tokens ("
            "contact_id INTEGER, app_id TEXT NOT NULL, type TEXT NOT NULL, "
            "create_datetime DATETIME NOT NULL, expire_datetime DATETIME, "
            "token TEXT PRIMARY KEY NOT NULL, data TEXT)"
        )

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(
            WaContactRow(
                id=ACTOR,
                name="Actor",
                login="actor",
                is_user=1,
                locale="en_US",
                create_datetime=NOW,
            )
        )
        session.add(
            WaContactRightRow(
                group_id=-ACTOR,
                app_id="team",
                name="add_users",
                value=1,
            )
        )
        await session.commit()

    publisher = InspectingContactsSavePublisher(sessions)
    service = InviteTeamUser(
        store=SQLAlchemyTeamInvitationStore(
            sessions,
            clock=lambda: NOW,
            token_factory=lambda: "x" * 32,
        ),
        event_publisher=publisher,
        access_uow_factory=SQLAlchemyAccessControlUnitOfWorkFactory(
            sessions
        ),
        rights_evaluator=RightsEvaluator(
            app_semantics=WebasystAccessSemantics(),
            fallback_policy=ExactThenLegacyAllFallback(),
        ),
        validator=LegacyTeamInvitationValidator(),
        hook=NoopInvitationHook(),
        link_builder=LegacyTeamInvitationLinkBuilder(
            "https://example.test/"
        ),
        email_sender=UnavailableTeamInvitationEmailSender(),
        waid=DisconnectedTeamWaidInvitationGateway(),
    )

    result = await service.execute(
        actor_contact_id=ACTOR,
        request=TeamInvitationCodeRequest(
            email=TeamTextPresent(value="new@example.test"),
        ),
    )

    assert isinstance(result, TeamInvitationLocalCodeCreated)
    assert publisher.contact_ids == [result.contact_id]

    async with sessions() as session:
        token = (
            await session.execute(
                text(
                    "SELECT type FROM wa_app_tokens "
                    "WHERE contact_id=:contact_id"
                ),
                {"contact_id": result.contact_id},
            )
        ).scalar_one()
        assert token == "waid_invite"

    await engine.dispose()
