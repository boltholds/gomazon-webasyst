from typing import Protocol

from gomazon_webasyst.contracts.team import TeamGroupRead


class TeamGroupReader(Protocol):
    async def list_ordered_by_sort(self) -> tuple[TeamGroupRead, ...]: ...
