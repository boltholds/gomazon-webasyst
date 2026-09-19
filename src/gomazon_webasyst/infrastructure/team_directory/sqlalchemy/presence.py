from datetime import datetime

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.ports.team_presence import (
    TeamPresenceReader,
    TeamPresenceSnapshot,
)
from gomazon_webasyst.application.team_directory.vo.presence import TeamPresence
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamDateTimeMissing,
    TeamDateTimeValue,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactSettingRow,
    WaLoginLogRow,
)


class SQLAlchemyTeamPresenceReader(TeamPresenceReader):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def read(
        self,
        contact_ids: tuple[int, ...],
    ) -> TeamPresenceSnapshot:
        if not contact_ids:
            return TeamPresenceSnapshot(())

        async with self._session_factory() as session:
            open_ids = set(
                (
                    await session.execute(
                        select(distinct(WaLoginLogRow.contact_id)).where(
                            WaLoginLogRow.contact_id.in_(contact_ids),
                            WaLoginLogRow.datetime_out.is_(None),
                        )
                    )
                ).scalars()
            )
            idle_rows = ()
            if open_ids:
                idle_rows = tuple(
                    (
                        await session.execute(
                            select(WaContactSettingRow).where(
                                WaContactSettingRow.contact_id.in_(
                                    tuple(open_ids)
                                ),
                                WaContactSettingRow.app_id == "webasyst",
                                WaContactSettingRow.name == "idle_since",
                            )
                        )
                    ).scalars()
                )

        idle_by_contact = {
            row.contact_id: _parse_idle_since(row.value)
            for row in idle_rows
        }
        return TeamPresenceSnapshot(
            tuple(
                TeamPresence(
                    contact_id=contact_id,
                    has_open_login=contact_id in open_ids,
                    idle_since=idle_by_contact.get(
                        contact_id,
                        TeamDateTimeMissing(),
                    ),
                )
                for contact_id in contact_ids
            )
        )


def _parse_idle_since(value: str):
    try:
        return TeamDateTimeValue(
            datetime.fromisoformat(value.replace(" ", "T"))
        )
    except ValueError as error:
        raise ValueError(
            f"invalid Webasyst idle_since datetime: {value!r}"
        ) from error
