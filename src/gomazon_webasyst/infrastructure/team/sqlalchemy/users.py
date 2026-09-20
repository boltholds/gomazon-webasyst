from collections.abc import Callable
from datetime import datetime, timezone, tzinfo

from pydantic import JsonValue
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    desc,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.team.ports import TeamUserReader
from gomazon_webasyst.contracts.enums import TeamUserOnlineStatus
from gomazon_webasyst.contracts.team import (
    TeamDateTimeMissing,
    TeamDateTimePresent,
    TeamEventMissing,
    TeamEventPresent,
    TeamEventValue,
    TeamIntegerMissing,
    TeamIntegerPresent,
    TeamTextMissing,
    TeamTextPresent,
    TeamUserPhone,
    TeamUserRead,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRow,
    WaUserGroupRow,
)


_METADATA = MetaData()

_APP_SETTINGS = Table(
    "wa_app_settings",
    _METADATA,
    Column("app_id", String(64), primary_key=True),
    Column("name", String(64), primary_key=True),
    Column("value", Text, nullable=False),
)

_CONTACT_SETTINGS = Table(
    "wa_contact_settings",
    _METADATA,
    Column("contact_id", Integer, primary_key=True),
    Column("app_id", String(32), primary_key=True),
    Column("name", String(64), primary_key=True),
    Column("value", Text, nullable=False),
)

_LOGIN_LOG = Table(
    "wa_login_log",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("contact_id", Integer, nullable=False),
    Column("datetime_in", DateTime, nullable=False),
    Column("datetime_out", DateTime),
    Column("ip", String(45)),
)

_CONTACT_CALENDARS = Table(
    "wa_contact_calendars",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("bg_color", String(7)),
    Column("font_color", String(7)),
    Column("status_bg_color", String(7)),
    Column("status_font_color", String(7)),
    Column("icon", String(255)),
)

_CONTACT_EVENTS = Table(
    "wa_contact_events",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("uid", String(255)),
    Column("create_datetime", DateTime, nullable=False),
    Column("update_datetime", DateTime, nullable=False),
    Column("contact_id", Integer, nullable=False),
    Column("calendar_id", Integer, nullable=False),
    Column("summary", String(255), nullable=False),
    Column("description", Text),
    Column("location", String(255)),
    Column("start", DateTime, nullable=False),
    Column("end", DateTime, nullable=False),
    Column("is_allday", Integer, nullable=False),
    Column("is_status", Integer, nullable=False),
    Column("sequence", Integer, nullable=False),
)

_ALLOWED_NAME_FIELDS = frozenset(
    {"firstname", "middlename", "lastname", "login"}
)


class SQLAlchemyTeamUserReader(TeamUserReader):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        server_timezone: tzinfo,
        clock: Callable[[], datetime],
    ) -> None:
        self._session_factory = session_factory
        self._server_timezone = server_timezone
        self._clock = clock

    async def list_candidates(
        self,
        group_ids: tuple[int, ...],
    ) -> tuple[TeamUserRead, ...]:
        async with self._session_factory() as session:
            contact_rows = await self._contact_rows(session, group_ids)
            if not contact_rows:
                return ()

            contact_ids = tuple(row.id for row in contact_rows)
            name_order = await self._name_order(session)
            emails = await self._emails(session, contact_ids)
            phones = await self._phones(session, contact_ids)
            groups = await self._groups(session, contact_ids)
            online = await self._online_statuses(
                session,
                contact_rows,
                contact_ids,
            )
            events = await self._current_events(session, contact_ids)

        users = tuple(
            self._to_user(
                row=row,
                name_order=name_order,
                emails=emails.get(row.id, ()),
                phones=phones.get(row.id, ()),
                group_ids=groups.get(row.id, ()),
                online_status=online[row.id],
                event=events.get(row.id, TeamEventMissing()),
            )
            for row in contact_rows
        )
        return tuple(sorted(users, key=lambda user: user.name.encode("utf-8")))

    async def _contact_rows(
        self,
        session: AsyncSession,
        group_ids: tuple[int, ...],
    ) -> tuple[WaContactRow, ...]:
        if group_ids:
            statement = (
                select(WaContactRow)
                .join(
                    WaUserGroupRow,
                    WaUserGroupRow.contact_id == WaContactRow.id,
                )
                .where(
                    WaUserGroupRow.group_id.in_(group_ids),
                    WaContactRow.is_user > 0,
                )
                .distinct()
            )
        else:
            statement = select(WaContactRow).where(
                WaContactRow.login.is_not(None),
                WaContactRow.is_user == 1,
            )
        result = await session.execute(statement)
        return tuple(result.scalars().unique().all())

    async def _name_order(
        self,
        session: AsyncSession,
    ) -> tuple[str, ...]:
        result = await session.execute(
            select(_APP_SETTINGS.c.value).where(
                _APP_SETTINGS.c.app_id == "webasyst",
                _APP_SETTINGS.c.name == "user_name_display",
            )
        )
        value = result.scalar_one_or_none()
        if value is None:
            return ("name",)
        if value == "":
            return ("firstname", "middlename", "lastname")
        return tuple(part.strip() for part in str(value).split(","))

    async def _emails(
        self,
        session: AsyncSession,
        contact_ids: tuple[int, ...],
    ) -> dict[int, tuple[str, ...]]:
        result = await session.execute(
            select(WaContactEmailRow)
            .where(WaContactEmailRow.contact_id.in_(contact_ids))
            .order_by(
                WaContactEmailRow.contact_id,
                WaContactEmailRow.sort,
            )
        )
        values: dict[int, list[str]] = {}
        for row in result.scalars():
            values.setdefault(row.contact_id, []).append(row.email)
        return {
            contact_id: tuple(items)
            for contact_id, items in values.items()
        }

    async def _phones(
        self,
        session: AsyncSession,
        contact_ids: tuple[int, ...],
    ) -> dict[int, tuple[TeamUserPhone, ...]]:
        result = await session.execute(
            select(WaContactDataRow)
            .where(
                WaContactDataRow.contact_id.in_(contact_ids),
                WaContactDataRow.field == "phone",
            )
            .order_by(
                WaContactDataRow.contact_id,
                WaContactDataRow.sort,
            )
        )
        values: dict[int, list[TeamUserPhone]] = {}
        for row in result.scalars():
            values.setdefault(row.contact_id, []).append(
                TeamUserPhone(
                    value=row.value,
                    ext=TeamTextPresent(value=row.ext),
                    status=(
                        TeamTextPresent(value=row.status)
                        if row.status is not None
                        else TeamTextMissing()
                    ),
                )
            )
        return {
            contact_id: tuple(items)
            for contact_id, items in values.items()
        }

    async def _groups(
        self,
        session: AsyncSession,
        contact_ids: tuple[int, ...],
    ) -> dict[int, tuple[int, ...]]:
        result = await session.execute(
            select(WaUserGroupRow)
            .where(WaUserGroupRow.contact_id.in_(contact_ids))
            .order_by(
                WaUserGroupRow.contact_id,
                WaUserGroupRow.group_id,
            )
        )
        values: dict[int, list[int]] = {}
        for row in result.scalars():
            values.setdefault(row.contact_id, []).append(row.group_id)
        return {
            contact_id: tuple(items)
            for contact_id, items in values.items()
        }

    async def _online_statuses(
        self,
        session: AsyncSession,
        contact_rows: tuple[WaContactRow, ...],
        contact_ids: tuple[int, ...],
    ) -> dict[int, TeamUserOnlineStatus]:
        now = self._local_now()
        active_result = await session.execute(
            select(_LOGIN_LOG.c.contact_id)
            .where(
                _LOGIN_LOG.c.contact_id.in_(contact_ids),
                _LOGIN_LOG.c.datetime_out.is_(None),
            )
            .distinct()
        )
        active_ids = frozenset(int(value) for value in active_result.scalars())

        idle_by_contact: dict[int, str] = {}
        if active_ids:
            idle_result = await session.execute(
                select(
                    _CONTACT_SETTINGS.c.contact_id,
                    _CONTACT_SETTINGS.c.value,
                ).where(
                    _CONTACT_SETTINGS.c.contact_id.in_(active_ids),
                    _CONTACT_SETTINGS.c.app_id == "webasyst",
                    _CONTACT_SETTINGS.c.name == "idle_since",
                )
            )
            idle_by_contact = {
                int(row.contact_id): str(row.value)
                for row in idle_result
            }

        statuses: dict[int, TeamUserOnlineStatus] = {}
        for row in contact_rows:
            status = TeamUserOnlineStatus.OFFLINE
            if (
                row.last_datetime is not None
                and (now - row.last_datetime).total_seconds() < 300
            ):
                status = TeamUserOnlineStatus.ONLINE
                idle_values = (
                    (idle_by_contact[row.id],)
                    if row.id in idle_by_contact
                    else ()
                )
                if idle_values:
                    idle_since = self._parse_legacy_datetime(idle_values[0])
                    if (now - idle_since).total_seconds() > 60:
                        status = TeamUserOnlineStatus.IDLE
            statuses[row.id] = status
        return statuses

    async def _current_events(
        self,
        session: AsyncSession,
        contact_ids: tuple[int, ...],
    ) -> dict[int, TeamEventValue]:
        now = self._local_now()
        statement = (
            select(
                _CONTACT_EVENTS,
                _CONTACT_CALENDARS.c.name.label("calendar_name"),
                _CONTACT_CALENDARS.c.status_bg_color,
                _CONTACT_CALENDARS.c.status_font_color,
                _CONTACT_CALENDARS.c.bg_color,
                _CONTACT_CALENDARS.c.font_color,
                _CONTACT_CALENDARS.c.icon,
            )
            .join(
                _CONTACT_CALENDARS,
                _CONTACT_CALENDARS.c.id
                == _CONTACT_EVENTS.c.calendar_id,
            )
            .where(
                _CONTACT_EVENTS.c.contact_id.in_(contact_ids),
                _CONTACT_EVENTS.c.is_status == 1,
                or_(
                    and_(
                        _CONTACT_EVENTS.c.is_allday == 0,
                        _CONTACT_EVENTS.c.start <= now,
                        _CONTACT_EVENTS.c.end >= now,
                    ),
                    and_(
                        _CONTACT_EVENTS.c.is_allday == 1,
                        func.date(_CONTACT_EVENTS.c.start)
                        <= func.date(now),
                        func.date(_CONTACT_EVENTS.c.end)
                        >= func.date(now),
                    ),
                ),
            )
            .order_by(
                desc(_CONTACT_EVENTS.c.is_allday),
                _CONTACT_EVENTS.c.start,
            )
        )
        result = await session.execute(statement)
        events: dict[int, TeamEventValue] = {}
        for row in result.mappings():
            contact_id = int(row["contact_id"])
            if contact_id in events:
                continue
            event = {
                key: self._json_value(row[key])
                for key in (
                    "id",
                    "uid",
                    "create_datetime",
                    "update_datetime",
                    "contact_id",
                    "calendar_id",
                    "summary",
                    "description",
                    "location",
                    "start",
                    "end",
                    "is_allday",
                    "is_status",
                    "sequence",
                    "calendar_name",
                    "status_bg_color",
                    "status_font_color",
                    "bg_color",
                    "font_color",
                    "icon",
                )
            }
            events[contact_id] = TeamEventPresent(value=event)
        return events

    def _to_user(
        self,
        *,
        row: WaContactRow,
        name_order: tuple[str, ...],
        emails: tuple[str, ...],
        phones: tuple[TeamUserPhone, ...],
        group_ids: tuple[int, ...],
        online_status: TeamUserOnlineStatus,
        event: TeamEventValue,
    ) -> TeamUserRead:
        return TeamUserRead(
            id=row.id,
            name=self._display_name(row, name_order),
            firstname=row.firstname,
            lastname=row.lastname,
            middlename=row.middlename,
            company=row.company,
            login=(
                TeamTextPresent(value=row.login)
                if row.login is not None
                else TeamTextMissing()
            ),
            email=emails,
            phone=phones,
            locale=row.locale,
            jobtitle=row.jobtitle,
            last_datetime=(
                TeamDateTimePresent(value=row.last_datetime)
                if row.last_datetime is not None
                else TeamDateTimeMissing()
            ),
            birth_day=(
                TeamIntegerPresent(value=row.birth_day)
                if row.birth_day is not None
                else TeamIntegerMissing()
            ),
            birth_month=(
                TeamIntegerPresent(value=row.birth_month)
                if row.birth_month is not None
                else TeamIntegerMissing()
            ),
            create_datetime=self._utc_datetime(row.create_datetime),
            online_status=online_status,
            event=event,
            group_ids=group_ids,
            photo_id=row.photo,
            is_company=bool(row.is_company),
        )

    @staticmethod
    def _display_name(
        row: WaContactRow,
        name_order: tuple[str, ...],
    ) -> str:
        parts: list[str] = []
        for field in name_order:
            if field not in _ALLOWED_NAME_FIELDS:
                continue
            value = getattr(row, field)
            if isinstance(value, str) and value:
                parts.append(value)
        formatted = " ".join(parts).strip()
        if formatted:
            return formatted
        if row.name:
            return row.name
        return f"user_id={row.id}"

    def _local_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is not None:
            value = value.astimezone(self._server_timezone).replace(tzinfo=None)
        return value

    def _utc_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=self._server_timezone)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _parse_legacy_datetime(value: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime(1970, 1, 1)

    @staticmethod
    def _json_value(value: object) -> JsonValue:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if value is None or isinstance(value, str | int | float | bool):
            return value
        return str(value)
