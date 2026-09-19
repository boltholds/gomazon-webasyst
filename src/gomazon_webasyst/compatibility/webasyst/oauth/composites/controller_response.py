from dataclasses import dataclass

from gomazon_webasyst.contracts.enums import ApiResponseFormat


@dataclass(slots=True, frozen=True)
class OAuthControllerPayloadResponse:
    status_code: int
    payload: dict[str, str]
    format: ApiResponseFormat


@dataclass(slots=True, frozen=True)
class OAuthControllerRenderedResponse:
    status_code: int
    media_type: str
    body: str
