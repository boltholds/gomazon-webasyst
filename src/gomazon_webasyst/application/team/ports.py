from typing import Protocol

from gomazon_webasyst.contracts.team import TeamGroupRead, TeamUserRead


class TeamGroupReader(Protocol):
    async def list_ordered_by_sort(self) -> tuple[TeamGroupRead, ...]: ...


class TeamUserReader(Protocol):
    async def list_candidates(
        self,
        group_ids: tuple[int, ...],
    ) -> tuple[TeamUserRead, ...]: ...
