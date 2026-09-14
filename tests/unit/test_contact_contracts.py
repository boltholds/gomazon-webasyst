from datetime import datetime

import pytest
from pydantic import ValidationError

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


def test_create_rejects_fields_owned_by_later_contact_slices() -> None:
    with pytest.raises(ValidationError):
        ContactCreate(name="Alice", email="alice@example.com")


def test_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        ContactUpdate()


def test_update_rejects_explicit_null_for_non_nullable_legacy_column() -> None:
    with pytest.raises(ValidationError):
        ContactUpdate(name=None)


def test_read_contract_is_frozen() -> None:
    contact = ContactRead(
        id=1,
        name="Alice",
        create_datetime=datetime(2026, 9, 14, 12, 0, 0),
    )
    with pytest.raises(ValidationError):
        contact.name = "Changed"
