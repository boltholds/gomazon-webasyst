from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.composition.session_state_providers import InMemorySessionStateStoreFactory
from tests.persistence_contracts.session_state_contract import (
    assert_session_state_store_contract,
)


class MemorySessionStateHarness:
    session_id = SessionId("contract-session")
    ttl = timedelta(seconds=5)

    def __init__(self) -> None:
        self._now = datetime(2026, 9, 19, 12, 0, 0)
        self.store = InMemorySessionStateStoreFactory(
            session_id_factory=lambda: self.session_id,
            clock=lambda: self._now,
            ttl=self.ttl,
        ).create()

    async def advance(self, delta: timedelta) -> None:
        self._now += delta


@pytest.mark.asyncio
async def test_in_memory_session_state_store_satisfies_shared_contract() -> None:
    await assert_session_state_store_contract(MemorySessionStateHarness())
