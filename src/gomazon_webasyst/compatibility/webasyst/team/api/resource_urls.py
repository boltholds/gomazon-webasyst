from dataclasses import dataclass
from urllib.parse import urljoin

from gomazon_webasyst.application.api_execution.vo.origin import ApiRequestOrigin
from gomazon_webasyst.application.team_directory.entities.user import TeamUser


@dataclass(slots=True, frozen=True)
class TeamUserResourceUrls:
    userpic: str
    original_crop: str
    uploaded: bool
    thumbs: dict[str, str]


class LegacyTeamUserResourceUrlPolicy:
    _SIZES = (16, 32, 96, 144)

    def project(
        self,
        user: TeamUser,
        origin: ApiRequestOrigin,
    ) -> TeamUserResourceUrls:
        if user.photo_stamp <= 0:
            fallback = urljoin(
                origin.value,
                "wa-content/img/userpic.svg",
            )
            return TeamUserResourceUrls(
                userpic=fallback,
                original_crop=fallback,
                uploaded=False,
                thumbs={
                    str(size): fallback
                    for size in self._SIZES
                },
            )

        directory = self._photo_directory(user.id)
        base = (
            "wa-data/public/contacts/photos/"
            f"{directory}{user.photo_stamp}"
        )
        thumbs = {
            str(size): urljoin(
                origin.value,
                f"{base}.{size}x{size}.jpg",
            )
            for size in self._SIZES
        }
        original_crop = urljoin(
            origin.value,
            f"{base}.jpg",
        )
        return TeamUserResourceUrls(
            userpic=thumbs["144"],
            original_crop=original_crop,
            uploaded=True,
            thumbs=thumbs,
        )

    @staticmethod
    def _photo_directory(contact_id: int) -> str:
        padded = str(contact_id).zfill(4)
        return (
            f"{padded[-2:]}/"
            f"{padded[-4:-2]}/"
            f"{contact_id}/"
        )
