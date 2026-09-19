from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.application.contacts import (
    CreateContact,
    DeleteContacts,
    GetContact,
    UpdateContact,
)
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate
from gomazon_webasyst.presentation.http.dependencies import get_container

router = APIRouter(prefix="/api/v1/contacts", tags=["contacts"])


def get_query(request: Request) -> GetContact:
    return get_container(request).get_contact


def get_creator(request: Request) -> CreateContact:
    return get_container(request).create_contact


def get_updater(request: Request) -> UpdateContact:
    return get_container(request).update_contact


def get_deleter(request: Request) -> DeleteContacts:
    return get_container(request).delete_contacts


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    use_case: Annotated[CreateContact, Depends(get_creator)],
) -> ContactRead:
    return await use_case.execute(data)


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: int,
    use_case: Annotated[GetContact, Depends(get_query)],
) -> ContactRead:
    return await use_case.execute(contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    use_case: Annotated[UpdateContact, Depends(get_updater)],
) -> ContactRead:
    return await use_case.execute(contact_id, data)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int,
    use_case: Annotated[DeleteContacts, Depends(get_deleter)],
) -> None:
    await use_case.execute(
        ContactDeletionBatch(contact_ids=(contact_id,))
    )
