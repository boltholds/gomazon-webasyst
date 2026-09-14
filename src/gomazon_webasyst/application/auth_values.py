from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SessionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("session id must not be empty")


@dataclass(slots=True, frozen=True)
class AuthSessionKey:
    contact_id: int
    session_id: SessionId

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("contact id must be positive")
