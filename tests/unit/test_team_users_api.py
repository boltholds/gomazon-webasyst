from datetime import datetime

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
    ApiPrincipalContext,
)
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiMethodName,
    ApiMethodTarget,
)
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.team.api import (
    TeamUsersGetListApiMethod,
)
from gomazon_webasyst.compatibility.webasyst.team.users_filter import (
    LegacyTeamUserFilterParser,
)
from gomazon_webasyst.compatibility.webasyst.team.users_media import (
    LegacyTeamUserMediaProjector,
    RootResourceUrlResolver,
)
from gomazon_webasyst.contracts.enums import TeamUserOnlineStatus
from gomazon_webasyst.contracts.team import (
    TeamDateTimeMissing,
    TeamEventMissing,
    TeamIntegerMissing,
    TeamTextMissing,
    TeamTextPresent,
    TeamUserPhone,
    TeamUserRead,
)


class FakeListUsers:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, *, contact_id, user_filter):
        self.calls.append((contact_id, user_filter))
        return (
            TeamUserRead(
                id=7,
                name="Alice Example",
                firstname="Alice",
                lastname="Example",
                middlename="",
                company="Example Ltd",
                login=TeamTextPresent(value="alice"),
                email=("a@example.test",),
                phone=(
                    TeamUserPhone(
                        value="123",
                        ext=TeamTextPresent(value="work"),
                        status=TeamTextMissing(),
                    ),
                ),
                locale="en_US",
                jobtitle="Engineer",
                last_datetime=TeamDateTimeMissing(),
                birth_day=TeamIntegerMissing(),
                birth_month=TeamIntegerMissing(),
                create_datetime=datetime(2026, 9, 20, 9, 0, 0),
                online_status=TeamUserOnlineStatus.OFFLINE,
                event=TeamEventMissing(),
                group_ids=(2, 3),
                photo_id=41,
                is_company=False,
            ),
        )


async def test_team_users_api_projects_legacy_shape_and_media() -> None:
    service = FakeListUsers()
    method = TeamUsersGetListApiMethod(
        list_users=service,
        filter_parser=LegacyTeamUserFilterParser(),
        media_projector=LegacyTeamUserMediaProjector(
            RootResourceUrlResolver("https://example.test/")
        ),
    )
    context = ApiInvocationContext(
        principal=ApiPrincipalContext(
            contact_id=42,
            client_id=ApiClientId("client"),
            scope=ApiScope.of("team"),
        ),
        target=ApiMethodTarget(
            AppId("team"),
            ApiMethodName("users.getList"),
        ),
    )
    parameters = ApiRequestParameters(
        query=ApiParameterMap({"filter[group_id]": "2"}),
        form=ApiParameterMap({}),
    )

    result = await method.execute(context, parameters)

    assert service.calls[0][0] == 42
    assert service.calls[0][1].group_ids == (2,)
    assert result.payload == [
        {
            "id": 7,
            "name": "Alice Example",
            "firstname": "Alice",
            "lastname": "Example",
            "middlename": "",
            "company": "Example Ltd",
            "login": "alice",
            "email": ["a@example.test"],
            "phone": [
                {
                    "value": "123",
                    "ext": "work",
                    "status": None,
                }
            ],
            "locale": "en_US",
            "jobtitle": "Engineer",
            "last_datetime": None,
            "_event": "",
            "birth_day": None,
            "birth_month": None,
            "create_datetime": "2026-09-20 09:00:00",
            "_online_status": "offline",
            "group_id": [2, 3],
            "userpic": (
                "https://example.test/wa-data/public/contacts/"
                "photos/07/00/7/41.144x144.jpg"
            ),
            "userpic_original_crop": (
                "https://example.test/wa-data/public/contacts/"
                "photos/07/00/7/41.jpg"
            ),
            "userpic_uploaded": True,
            "userpic_thumbs": {
                "16": (
                    "https://example.test/wa-data/public/contacts/"
                    "photos/07/00/7/41.16x16.jpg"
                ),
                "32": (
                    "https://example.test/wa-data/public/contacts/"
                    "photos/07/00/7/41.32x32.jpg"
                ),
                "96": (
                    "https://example.test/wa-data/public/contacts/"
                    "photos/07/00/7/41.96x96.jpg"
                ),
                "144": (
                    "https://example.test/wa-data/public/contacts/"
                    "photos/07/00/7/41.144x144.jpg"
                ),
            },
        }
    ]


def test_default_userpic_uses_team_ui_2_svg() -> None:
    user = TeamUserRead(
        id=9,
        name="No Photo",
        firstname="",
        lastname="",
        middlename="",
        company="",
        login=TeamTextMissing(),
        email=(),
        phone=(),
        locale="",
        jobtitle="",
        last_datetime=TeamDateTimeMissing(),
        birth_day=TeamIntegerMissing(),
        birth_month=TeamIntegerMissing(),
        create_datetime=datetime(2026, 9, 20, 9, 0, 0),
        online_status=TeamUserOnlineStatus.OFFLINE,
        event=TeamEventMissing(),
        group_ids=(),
        photo_id=0,
        is_company=False,
    )
    projection = LegacyTeamUserMediaProjector(
        RootResourceUrlResolver("https://example.test")
    ).project(user)

    assert projection["userpic"] == (
        "https://example.test/wa-content/img/userpic.svg"
    )
    assert projection["userpic_original_crop"] == projection["userpic"]
    assert projection["userpic_uploaded"] is False
    assert set(projection["userpic_thumbs"].values()) == {
        "https://example.test/wa-content/img/userpic.svg"
    }
