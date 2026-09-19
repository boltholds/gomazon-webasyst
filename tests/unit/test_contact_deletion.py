import pytest

from gomazon_webasyst.application.contact_deletion import (
    ContactDeletionApplied,
    ContactDeletionBatch,
)
from gomazon_webasyst.application.contacts import DeleteContacts
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
    EventHandlerFailureDiagnostic,
)
from gomazon_webasyst.application.events.vo.identity import EventHandlerId
from gomazon_webasyst.application.events.vo.owners import ApplicationEventOwner
from gomazon_webasyst.application.events.vo.contacts import (
    ContactsDeleteEventPayload,
)
from gomazon_webasyst.application.access_values import AppId


class RecordingContacts:
    def __init__(self, sequence: list[str]) -> None:
        self.sequence = sequence
        self.batches = []

    async def delete_batch(self, batch):
        self.sequence.append("delete")
        self.batches.append(batch)
        return ContactDeletionApplied(contact_ids=batch.contact_ids)


class RecordingUow:
    def __init__(self, sequence: list[str]) -> None:
        self.sequence = sequence
        self.contacts = RecordingContacts(sequence)
        self.commits = 0

    async def __aenter__(self):
        self.sequence.append("uow_enter")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.sequence.append("uow_exit")

    async def commit(self):
        self.sequence.append("commit")
        self.commits += 1

    async def rollback(self):
        self.sequence.append("rollback")


class RecordingUowFactory:
    def __init__(self, sequence: list[str]) -> None:
        self.sequence = sequence
        self.created = []

    def __call__(self):
        uow = RecordingUow(self.sequence)
        self.created.append(uow)
        return uow


class RecordingPublisher:
    def __init__(self, sequence: list[str], *, fail: bool = False) -> None:
        self.sequence = sequence
        self.fail = fail
        self.requests = []

    async def publish(self, request):
        self.sequence.append("publish")
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("publisher failed")
        return EventDispatchReport(
            event=request.event,
            results=(),
            failures=(
                EventHandlerFailureDiagnostic(
                    handler_id=EventHandlerId("failed-handler"),
                    owner=ApplicationEventOwner(AppId("blog")),
                    error_type="RuntimeError",
                    message="ignored ordinary handler failure",
                ),
            ),
        )


def test_contact_deletion_batch_requires_positive_nonempty_ids_and_preserves_duplicates() -> None:
    assert ContactDeletionBatch(contact_ids=(3, 1, 3)).contact_ids == (3, 1, 3)
    with pytest.raises(ValueError):
        ContactDeletionBatch(contact_ids=())
    with pytest.raises(ValueError):
        ContactDeletionBatch(contact_ids=(1, 0))


@pytest.mark.asyncio
async def test_delete_contacts_publishes_before_destructive_uow_and_preserves_batch() -> None:
    sequence: list[str] = []
    publisher = RecordingPublisher(sequence)
    uows = RecordingUowFactory(sequence)
    use_case = DeleteContacts(uows, publisher)
    batch = ContactDeletionBatch(contact_ids=(3, 1, 3))

    result = await use_case.execute(batch)

    assert sequence == [
        "publish",
        "uow_enter",
        "delete",
        "commit",
        "uow_exit",
    ]
    assert result == ContactDeletionApplied(contact_ids=(3, 1, 3))
    assert uows.created[0].contacts.batches == [batch]

    request = publisher.requests[0]
    assert request.event.app_id == AppId("contacts")
    assert request.event.name.value == "delete"
    assert isinstance(request.payload, ContactsDeleteEventPayload)
    assert request.payload.contact_ids == (3, 1, 3)


@pytest.mark.asyncio
async def test_recorded_handler_failures_do_not_cancel_contact_cleanup() -> None:
    sequence: list[str] = []
    use_case = DeleteContacts(
        RecordingUowFactory(sequence),
        RecordingPublisher(sequence),
    )

    await use_case.execute(ContactDeletionBatch(contact_ids=(1,)))

    assert "delete" in sequence
    assert "commit" in sequence


@pytest.mark.asyncio
async def test_publisher_exception_prevents_destructive_uow_from_starting() -> None:
    sequence: list[str] = []
    use_case = DeleteContacts(
        RecordingUowFactory(sequence),
        RecordingPublisher(sequence, fail=True),
    )

    with pytest.raises(RuntimeError, match="publisher failed"):
        await use_case.execute(ContactDeletionBatch(contact_ids=(1,)))

    assert sequence == ["publish"]
