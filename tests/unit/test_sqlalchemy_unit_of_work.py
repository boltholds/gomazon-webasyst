import pytest

from gomazon_webasyst.infrastructure.persistence.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWorkFactory


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def close(self) -> None:
        self.closes += 1


class FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = FakeSession()
        self.sessions.append(session)
        return session


@pytest.mark.asyncio
async def test_uow_commit_and_close() -> None:
    sessions = FakeSessionFactory()
    factory = SQLAlchemyUnitOfWorkFactory(sessions)  # type: ignore[arg-type]
    async with factory() as uow:
        await uow.commit()
    session = sessions.sessions[0]
    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closes == 1


@pytest.mark.asyncio
async def test_uow_rolls_back_on_exception_and_closes() -> None:
    sessions = FakeSessionFactory()
    factory = SQLAlchemyUnitOfWorkFactory(sessions)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        async with factory():
            raise RuntimeError("boom")
    session = sessions.sessions[0]
    assert session.rollbacks == 1
    assert session.closes == 1
