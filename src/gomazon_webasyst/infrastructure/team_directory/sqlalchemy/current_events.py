from datetime import datetime

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.ports.team_current_events import (
    TeamCurrentEventReader,
    TeamCurrentEventSnapshot,
    TeamUserCurrentEvent,
)
from gomazon_webasyst.application.team_directory.entities.current_event import (
    TeamCurrentEvent,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamCurrentEventMissing,
    TeamCurrentEventPresent,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactCalendarRow,
    WaContactEventRow,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.states import (
    text_state,
)


class SQLAlchemyTeamCurrentEventReader(TeamCurrentEventReader):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def current_for_users(
        self,
        contact_ids: tuple[int, ...],
        now: datetime,
    ) -> TeamCurrentEventSnapshot:
        if not contact_ids:
            return TeamCurrentEventSnapshot(())

        async with self._session_factory() as session:
            rows = await session.execute(
                select(WaContactEventRow, WaContactCalendarRow)
                .join(
                    WaContactCalendarRow,
                    WaContactCalendarRow.id
                    == WaContactEventRow.calendar_id,
                )
                .where(
                    WaContactEventRow.contact_id.in_(contact_ids),
                    WaContactEventRow.is_status == 1,
                    or_(
                        and_(
                            WaContactEventRow.is_allday == 0,
                            WaContactEventRow.start <= now,
                            WaContactEventRow.end >= now,
                        ),
                        and_(
                            WaContactEventRow.is_allday == 1,
                            func.date(WaContactEventRow.start)
                            <= func.date(now),
                            func.date(WaContactEventRow.end)
                            >= func.date(now),
                        ),
                    ),
                )
                .order_by(
                    desc(WaContactEventRow.is_allday),
                    WaContactEventRow.start,
                    WaContactEventRow.id,
                )
            )

        first_by_contact: dict[int, TeamCurrentEvent] = {}
        for event, calendar in rows:
            if event.contact_id in first_by_contact:
                continue
            first_by_contact[event.contact_id] = TeamCurrentEvent(
                id=event.id,
                uid=text_state(event.uid),
                create_datetime=event.create_datetime,
                update_datetime=event.update_datetime,
                contact_id=event.contact_id,
                calendar_id=event.calendar_id,
                summary=event.summary,
                description=text_state(event.description),
                location=text_state(event.location),
                start=event.start,
                end=event.end,
                is_allday=bool(event.is_allday),
                is_status=bool(event.is_status),
                sequence=event.sequence,
                calendar_name=calendar.name,
                status_bg_color=text_state(calendar.status_bg_color),
                status_font_color=text_state(calendar.status_font_color),
                bg_color=text_state(calendar.bg_color),
                font_color=text_state(calendar.font_color),
                icon=text_state(calendar.icon),
            )

        return TeamCurrentEventSnapshot(
            tuple(
                TeamUserCurrentEvent(
                    contact_id=contact_id,
                    state=(
                        TeamCurrentEventPresent(
                            first_by_contact[contact_id]
                        )
                        if contact_id in first_by_contact
                        else TeamCurrentEventMissing()
                    ),
                )
                for contact_id in contact_ids
            )
        )
