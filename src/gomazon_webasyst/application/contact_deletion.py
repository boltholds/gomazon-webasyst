from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ContactDeletionBatch:
    contact_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.contact_ids:
            raise ValueError("contact deletion batch must not be empty")
        if any(contact_id <= 0 for contact_id in self.contact_ids):
            raise ValueError("contact deletion ids must be positive")


@dataclass(slots=True, frozen=True)
class ContactDeletionApplied:
    contact_ids: tuple[int, ...]
