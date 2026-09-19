from datetime import datetime

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.application.api_execution.vo.origin import ApiRequestOrigin
from gomazon_webasyst.application.team_directory.entities.user import TeamUser
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamCurrentEventMissing,
    TeamDateTimeMissing,
    TeamIntMissing,
)
from gomazon_webasyst.compatibility.webasyst.team.api.resource_urls import (
    LegacyTeamUserResourceUrlPolicy,
)
from gomazon_webasyst.contracts.enums import TeamOnlineStatus


def user(contact_id: int, photo_stamp: int) -> TeamUser:
    return TeamUser(
        id=contact_id,
        name="User",
        firstname="User",
        lastname="",
        middlename="",
        company="",
        login="user",
        emails=(),
        phones=(),
        locale="en_US",
        jobtitle="",
        last_datetime=TeamDateTimeMissing(),
        birth_day=TeamIntMissing(),
        birth_month=TeamIntMissing(),
        create_datetime=datetime(2026, 1, 1),
        photo_stamp=photo_stamp,
        group_ids=(GroupId(1),),
        online_status=TeamOnlineStatus.OFFLINE,
        current_event=TeamCurrentEventMissing(),
    )


def test_no_photo_uses_ui2_userpic_svg_for_all_team_userpic_fields() -> None:
    urls = LegacyTeamUserResourceUrlPolicy().project(
        user(42, 0),
        ApiRequestOrigin("https://example.test/root/"),
    )
    expected = "https://example.test/root/wa-content/img/userpic.svg"
    assert urls.userpic == expected
    assert urls.original_crop == expected
    assert urls.uploaded is False
    assert set(urls.thumbs) == {"16", "32", "96", "144"}
    assert set(urls.thumbs.values()) == {expected}


def test_uploaded_photo_uses_legacy_contact_directory_and_sizes() -> None:
    urls = LegacyTeamUserResourceUrlPolicy().project(
        user(42, 12345),
        ApiRequestOrigin("https://example.test/"),
    )
    prefix = (
        "https://example.test/wa-data/public/contacts/photos/"
        "42/00/42/12345"
    )
    assert urls.userpic == prefix + ".144x144.jpg"
    assert urls.original_crop == prefix + ".jpg"
    assert urls.thumbs["16"] == prefix + ".16x16.jpg"
    assert urls.thumbs["32"] == prefix + ".32x32.jpg"
    assert urls.thumbs["96"] == prefix + ".96x96.jpg"
    assert urls.uploaded is True
