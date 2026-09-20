import json
import re
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.ports.team_invitation import TeamInvitationStore
from gomazon_webasyst.contracts.enums import (
    TeamInvitationChannel,
    TeamInvitationRejectReason,
)
from gomazon_webasyst.contracts.team import TeamTextPresent
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationCodeRequest,
    TeamInvitationContactConflict,
    TeamInvitationEmailLinkRequest,
    TeamInvitationPhoneLinkRequest,
    TeamInvitationPrepared,
    TeamInvitationRequest,
    TeamInvitationStoreResult,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaAppTokenRow,
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRow,
)


_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789(!-_~*)"
_TTL = timedelta(days=3)
_TOKEN_LIMIT = 5


class SQLAlchemyTeamInvitationStore(TeamInvitationStore):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        clock: Callable[[], datetime],
        token_factory: Callable[[], str] = lambda: "".join(
            secrets.choice(_ALPHABET) for _ in range(32)
        ),
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._token_factory = token_factory

    async def prepare(
        self,
        *,
        actor_contact_id: int,
        request: TeamInvitationRequest,
        manageable_group_ids: tuple[int, ...],
    ) -> TeamInvitationStoreResult:
        actor_locale = await self._actor_locale(actor_contact_id)

        if isinstance(request, TeamInvitationCodeRequest):
            email = (
                request.email.value
                if isinstance(request.email, TeamTextPresent)
                else ""
            )
            phone = (
                request.phone.value
                if isinstance(request.phone, TeamTextPresent)
                else ""
            )
            contact = await self._create_contact_committed(
                actor_contact_id=actor_contact_id,
                locale="",
                email=email,
                phone=phone,
            )
            token_type = "waid_invite"
            channel = TeamInvitationChannel.CODE
            recipient_locale = ""
        else:
            assert isinstance(
                request,
                TeamInvitationEmailLinkRequest
                | TeamInvitationPhoneLinkRequest,
            )
            if isinstance(request, TeamInvitationPhoneLinkRequest):
                found = await self._find_by_phone(request.phone)
                email = ""
                phone = request.phone
                channel = TeamInvitationChannel.PHONE
            else:
                found = await self._find_by_email(request.email)
                email = request.email
                phone = ""
                channel = TeamInvitationChannel.EMAIL

            if found:
                conflict = self._conflict(found[0])
                if conflict:
                    return conflict[0]
                contact = found[0]
            else:
                contact = await self._create_contact_committed(
                    actor_contact_id=actor_contact_id,
                    locale=actor_locale,
                    email=email,
                    phone=phone,
                )
            token_type = "user_invite"
            recipient_locale = contact.locale or actor_locale

        token = await self._create_token_committed(
            contact_id=contact.id,
            token_type=token_type,
            manageable_group_ids=manageable_group_ids,
            include_groups=bool(request.requested_groups),
        )
        await self._trim_tokens_committed(
            contact_id=contact.id,
            token_type=token_type,
        )
        return TeamInvitationPrepared(
            contact_id=contact.id,
            token=token.token,
            expires_at=int(token.expire_datetime.timestamp()),
            channel=channel,
            recipient_locale=recipient_locale,
        )

    async def delete_token(self, token: str) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(WaAppTokenRow).where(
                        WaAppTokenRow.token == token
                    )
                )

    async def _actor_locale(self, contact_id: int) -> str:
        async with self._session_factory() as session:
            row = await session.get(WaContactRow, contact_id)
            return row.locale if row is not None else ""

    async def _find_by_email(
        self,
        email: str,
    ) -> tuple[WaContactRow, ...]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WaContactRow)
                .join(
                    WaContactEmailRow,
                    WaContactEmailRow.contact_id == WaContactRow.id,
                )
                .where(WaContactEmailRow.email == email)
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return ()
            session.expunge(row)
            return (row,)

    async def _find_by_phone(
        self,
        phone: str,
    ) -> tuple[WaContactRow, ...]:
        cleaned = self._clean_phone(phone)
        async with self._session_factory() as session:
            result = await session.execute(
                select(WaContactRow)
                .join(
                    WaContactDataRow,
                    WaContactDataRow.contact_id == WaContactRow.id,
                )
                .where(
                    WaContactDataRow.field == "phone",
                    WaContactDataRow.value == cleaned,
                )
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return ()
            session.expunge(row)
            return (row,)

    async def _create_contact_committed(
        self,
        *,
        actor_contact_id: int,
        locale: str,
        email: str,
        phone: str,
    ) -> WaContactRow:
        async with self._session_factory() as session:
            async with session.begin():
                name = email.split("@", 1)[0] if email else ""
                row = WaContactRow(
                    name=name,
                    is_user=0,
                    create_datetime=self._clock(),
                    create_app_id="team",
                    create_method="invite",
                    create_contact_id=actor_contact_id,
                    locale=locale,
                )
                session.add(row)
                await session.flush()
                if email:
                    session.add(
                        WaContactEmailRow(
                            contact_id=row.id,
                            email=email,
                            sort=0,
                        )
                    )
                if phone:
                    session.add(
                        WaContactDataRow(
                            contact_id=row.id,
                            field="phone",
                            ext="",
                            value=self._clean_phone(phone),
                            sort=0,
                        )
                    )
                await session.flush()
                contact_id = row.id
            detached = await session.get(WaContactRow, contact_id)
            assert detached is not None
            session.expunge(detached)
            return detached

    async def _create_token_committed(
        self,
        *,
        contact_id: int,
        token_type: str,
        manageable_group_ids: tuple[int, ...],
        include_groups: bool,
    ) -> WaAppTokenRow:
        now = self._clock()
        expires = now + _TTL
        token_data: dict[str, object] = {"full_access": False}
        if include_groups:
            token_data["groups"] = list(manageable_group_ids)
        token = self._token_factory()

        async with self._session_factory() as session:
            async with session.begin():
                row = WaAppTokenRow(
                    token=token,
                    contact_id=contact_id,
                    app_id="team",
                    type=token_type,
                    create_datetime=now,
                    expire_datetime=expires,
                    data=json.dumps(
                        token_data,
                        separators=(",", ":"),
                    ),
                )
                session.add(row)
                await session.flush()
            detached = await session.get(WaAppTokenRow, token)
            assert detached is not None
            session.expunge(detached)
            return detached

    async def _trim_tokens_committed(
        self,
        *,
        contact_id: int,
        token_type: str,
    ) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(WaAppTokenRow.token)
                    .where(
                        WaAppTokenRow.app_id == "team",
                        WaAppTokenRow.type == token_type,
                        WaAppTokenRow.contact_id == contact_id,
                    )
                    .order_by(WaAppTokenRow.create_datetime.desc())
                    .limit(_TOKEN_LIMIT)
                )
                keep = tuple(result.scalars())
                if keep:
                    await session.execute(
                        delete(WaAppTokenRow).where(
                            WaAppTokenRow.app_id == "team",
                            WaAppTokenRow.type == token_type,
                            WaAppTokenRow.contact_id == contact_id,
                            WaAppTokenRow.token.not_in(keep),
                        )
                    )

    @staticmethod
    def _conflict(
        contact: WaContactRow,
    ) -> tuple[TeamInvitationContactConflict, ...]:
        if contact.is_user == 0:
            return ()
        reason = (
            TeamInvitationRejectReason.CONTACT_BANNED
            if contact.is_user == -1 and bool(contact.login)
            else TeamInvitationRejectReason.USER_IN_TEAM
        )
        return (
            TeamInvitationContactConflict(
                reason=reason,
                contact_id=contact.id,
            ),
        )

    @staticmethod
    def _clean_phone(value: str) -> str:
        cleaned = value.strip()
        for char in "+-()":
            cleaned = cleaned.replace(char, "")
        return re.sub(r"(\d)\s+(\d)", r"\1\2", cleaned)
