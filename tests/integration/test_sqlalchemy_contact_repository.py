import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactMissing, ContactResolved
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.repositories import SQLAlchemyContactRepository
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWorkFactory
from tests.persistence_contracts.contacts_contract import assert_contact_repository_contract


async def make_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine


@pytest.mark.asyncio
async def test_sqlalchemy_repository_satisfies_contact_contract() -> None:
    engine = await make_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await assert_contact_repository_contract(SQLAlchemyContactRepository(session))
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_uow_commit_is_visible_to_next_uow() -> None:
    engine = await make_engine()
    factory = SQLAlchemyUnitOfWorkFactory(async_sessionmaker(engine, expire_on_commit=False))
    async with factory() as first:
        created = await first.contacts.create(ContactCreate(name="Committed"))
        await first.commit()
    async with factory() as second:
        loaded = await second.contacts.get(created.id)
    assert isinstance(loaded, ContactResolved)
    assert loaded.contact.name == "Committed"
    await engine.dispose()


@pytest.mark.asyncio
async def test_uow_exception_rolls_back() -> None:
    engine = await make_engine()
    factory = SQLAlchemyUnitOfWorkFactory(async_sessionmaker(engine, expire_on_commit=False))
    created_id = 0
    with pytest.raises(RuntimeError):
        async with factory() as first:
            created = await first.contacts.create(ContactCreate(name="Rolled back"))
            created_id = created.id
            raise RuntimeError("force rollback")
    assert created_id > 0
    async with factory() as second:
        assert await second.contacts.get(created_id) == ContactMissing(contact_id=created_id)
    await engine.dispose()
