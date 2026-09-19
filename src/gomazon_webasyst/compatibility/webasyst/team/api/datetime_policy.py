from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(slots=True, frozen=True)
class LegacyTeamDateTimePolicy:
    server_timezone: ZoneInfo

    @classmethod
    def from_name(cls, name: str) -> "LegacyTeamDateTimePolicy":
        try:
            return cls(ZoneInfo(name))
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                f"unknown Webasyst timezone: {name!r}"
            ) from error

    def create_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:
            source = value.replace(tzinfo=self.server_timezone)
        else:
            source = value
        return source.astimezone(UTC).replace(
            tzinfo=None
        ).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def local_datetime(value: datetime) -> str:
        return value.replace(tzinfo=None).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
