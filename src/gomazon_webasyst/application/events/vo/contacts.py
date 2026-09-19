from gomazon_webasyst.application.events.vo.payload import EventPayload


class ContactsDeleteEventPayload(EventPayload):
    contact_ids: tuple[int, ...]
