from gomazon_webasyst.application.ports.contacts import ContactRepository
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactUpdate


async def assert_contact_repository_contract(repo: ContactRepository) -> None:
    created = await repo.create(ContactCreate(name="Alice", firstname="Alice"))
    assert created.id > 0
    assert created.name == "Alice"
    assert await repo.get(created.id) == created

    updated = await repo.update(created.id, ContactUpdate(company="Example Ltd"))
    assert updated is not None
    assert updated.company == "Example Ltd"

    assert await repo.get(999_999) is None
