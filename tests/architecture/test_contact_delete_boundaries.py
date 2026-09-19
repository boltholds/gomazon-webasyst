import ast
from pathlib import Path

from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch


CONTACTS = Path("src/gomazon_webasyst/application/contacts.py")
DELETION = Path("src/gomazon_webasyst/application/contact_deletion.py")


def test_contact_deletion_batch_is_immutable_and_uses_tuple_scope() -> None:
    batch = ContactDeletionBatch(contact_ids=(3, 1, 3))
    assert batch.contact_ids == (3, 1, 3)
    source = DELETION.read_text(encoding="utf-8")
    assert "@dataclass(slots=True, frozen=True)" in source
    assert "contact_ids: tuple[int, ...]" in source


def test_delete_contacts_depends_on_event_publisher_port_not_concrete_runtime() -> None:
    source = CONTACTS.read_text(encoding="utf-8")
    assert "application.ports.event_publisher" in source
    assert "EventPublisher" in source
    assert "EventDispatcher" not in source
    assert "InMemoryEventHandlerRegistry" not in source


def test_delete_contacts_publishes_before_uow_entry_in_source_order() -> None:
    tree = ast.parse(CONTACTS.read_text(encoding="utf-8"))
    target = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "DeleteContacts"
    )
    execute = next(
        node
        for node in target.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute"
    )
    publish_line = min(
        node.lineno
        for node in ast.walk(execute)
        if isinstance(node, ast.Attribute) and node.attr == "publish"
    )
    uow_line = min(
        node.lineno
        for node in ast.walk(execute)
        if isinstance(node, ast.AsyncWith)
    )
    assert publish_line < uow_line
