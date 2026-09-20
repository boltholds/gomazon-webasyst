import json
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.ports.team_invitation import TeamInvitationStore
from gomazon_webasyst.contracts.enums import (
    TeamInvitationChannel,
    TeamInvitationMode,
    TeamInvitationRejectReason,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationContactConflict,
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
        async with self._session_factory() as session:
            async with session.begin():
                actor = await session.get(WaContactRow, actor_contact_id)
                actor_locale = actor.locale if actor is not None else ""

                if request.mode is TeamInvitationMode.CODE:
                    contact = await self._create_contact(
                        session,
                        actor_contact_id=actor_contact_id,
                        actor_locale=actor_locale,
                        email=(
                            request.email
                            if self._php_array_filter_truthy(request.email)
                            else ""
                        ),
                        phone=(
                            request.phone
                            if self._php_array_filter_truthy(request.phone)
                            else ""
                        ),
                    )
                    token_type = "waid_invite"
                    channel = TeamInvitationChannel.CODE
                else:
                    use_phone = self._php_truthy_string(request.phone)
                    found = (
                        await self._find_by_phone(session, request.phone)
                        if use_phone
                        else await self._find_by_email(session, request.email)
                    )
                    if found:
                        conflict = self._conflict(found[0])
                        if conflict:
                            return conflict
                        contact = found[0]
                    else:
                        contact = await self._create_contact(
                            session,
                            actor_contact_id=actor_contact_id,
                            actor_locale=actor_locale,
                            email="" if use_phone else request.email,
                            phone=request.phone if use_phone else "",
                        )
                    token_type = "user_invite"
                    channel = (
                        TeamInvitationChannel.PHONE
                        if use_phone
                        else TeamInvitationChannel.EMAIL
                    )

                now = self._clock()
                expires = now + _TTL
                token = await self._unique_token(session)
                token_data: dict[str, object] = {"full_access": False}
                if request.group_ids:
                    token_data["groups"] = list(manageable_group_ids)
                session.add(
                    WaAppTokenRow(
                        token=token,
                        contact_id=contact.id,
                        app_id="team",
                        type=token_type,
                        create_datetime=now,
                        expire_datetime=expires,
                        data=json.dumps(
                            token_data,
                            separators=(",", ":"),
                        ),
                    )
                )
                await session.flush()
                await self._trim_tokens(
                    session,
                    contact_id=contact.id,
                    token_type=token_type,
                )
                return TeamInvitationPrepared(
                    contact_id=contact.id,
                    token=token,
                    expires_at=int(expires.timestamp()),
                    channel=channel,
                )

    async def delete_token(self, token: str) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(WaAppTokenRow).where(
                        WaAppTokenRow.token == token
                    )
                )

    async def _find_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> tuple[WaContactRow, ...]:
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
        return (row,) if row is not None else ()

    async def _find_by_phone(
        self,
        session: AsyncSession,
        phone: str,
    ) -> tuple[WaContactRow, ...]:
        cleaned = self._clean_phone(phone)
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
        return (row,) if row is not None else ()

    async def _create_contact(
        self,
        session: AsyncSession,
        *,
        actor_contact_id: int,
        actor_locale: str,
        email: str,
        phone: str,
    ) -> WaContactRow:
        name = email.split("@", 1)[0] if email else ""
        row = WaContactRow(
            name=name,
            is_user=0,
            create_datetime=self._clock(),
            create_app_id="team",
            create_method="invite",
            create_contact_id=actor_contact_id,
            locale=actor_locale,
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
        return row

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

    async def _unique_token(self, session: AsyncSession) -> str:
        for _ in range(32):
            token = self._token_factory()
            existing = await session.get(WaAppTokenRow, token)
            if existing is None:
                return token
        raise RuntimeError("unable to allocate unique team invitation token")

    async def _trim_tokens(
        self,
        session: AsyncSession,
        *,
        contact_id: int,
        token_type: str,
    ) -> None:
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
    def _clean_phone(value: str) -> str:
        cleaned = value.strip()
        for char in "+-()":
            cleaned = cleaned.replace(char, "")
        pieces = cleaned.split()
        return "".join(pieces)

    @staticmethod
    def _php_truthy_string(value: str) -> bool:
        return value not in {"", "0"}

    @staticmethod
    def _php_array_filter_truthy(value: str) -> bool:
        return value not in {"", "0"}
