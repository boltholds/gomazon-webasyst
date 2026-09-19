from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


@dataclass(slots=True, frozen=True)
class ApiRequestOrigin:
    value: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("API request origin must be an absolute HTTP(S) URL")
        if parsed.query or parsed.fragment:
            raise ValueError("API request origin must not contain query or fragment")
        path = parsed.path or "/"
        if not path.endswith("/"):
            path += "/"
        normalized = urlunsplit(
            (parsed.scheme.lower(), parsed.netloc, path, "", "")
        )
        object.__setattr__(self, "value", normalized)
