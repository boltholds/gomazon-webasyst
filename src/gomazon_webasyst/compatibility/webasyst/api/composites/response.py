from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ApiTransportResponse:
    status_code: int
    media_type: str
    body: str
    headers: tuple[tuple[str, str], ...] = ()
