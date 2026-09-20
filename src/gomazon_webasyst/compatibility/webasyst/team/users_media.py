from dataclasses import dataclass

from pydantic import JsonValue

from gomazon_webasyst.contracts.team import TeamUserRead


@dataclass(slots=True, frozen=True)
class RootResourceUrlResolver:
    public_root_url: str

    def absolute(self, relative_url: str) -> str:
        root = self.public_root_url.rstrip("/")
        path = relative_url.lstrip("/")
        return f"{root}/{path}"


@dataclass(slots=True, frozen=True)
class LegacyTeamUserMediaProjector:
    resources: RootResourceUrlResolver
    ui_version: str = "2.0"

    def project(self, user: TeamUserRead) -> dict[str, JsonValue]:
        return {
            "userpic": self._photo_url(user, 144),
            "userpic_original_crop": self._photo_url(
                user,
                "original_crop",
            ),
            "userpic_uploaded": user.photo_id > 0,
            "userpic_thumbs": {
                str(size): self._photo_url(user, size)
                for size in (16, 32, 96, 144)
            },
        }

    def _photo_url(
        self,
        user: TeamUserRead,
        size: int | str,
    ) -> str:
        if user.photo_id > 0:
            contact = str(user.id).rjust(4, "0")
            directory = (
                f"{contact[-2:]}/{contact[-4:-2]}/{user.id}/"
            )
            filename = (
                f"{user.photo_id}.jpg"
                if size == "original_crop"
                else f"{user.photo_id}.{int(size)}x{int(size)}.jpg"
            )
            return self.resources.absolute(
                "wa-data/public/contacts/photos/"
                f"{directory}{filename}"
            )

        if self.ui_version == "2.0":
            image = "company.svg" if user.is_company else "userpic.svg"
            return self.resources.absolute(f"wa-content/img/{image}")

        numeric_size = int(size) if isinstance(size, int) else 0
        if numeric_size not in {20, 32, 50, 96}:
            numeric_size = 96
        prefix = "company" if user.is_company else "userpic"
        return self.resources.absolute(
            f"wa-content/img/{prefix}{numeric_size}.jpg"
        )
