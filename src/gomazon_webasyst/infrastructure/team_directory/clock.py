from datetime import datetime

from gomazon_webasyst.application.ports.team_clock import TeamClock


class SystemTeamClock(TeamClock):
    def now(self) -> datetime:
        return datetime.now()
