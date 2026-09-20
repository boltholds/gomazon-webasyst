from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.api.services.parameter_reader import (
    ApiParameterRejected,
)
from gomazon_webasyst.compatibility.webasyst.team.invitation import (
    LegacyTeamInvitationRequestParser,
)
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode
from gomazon_webasyst.contracts.team import TeamTextMissing, TeamTextPresent
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationCodeRequest,
    TeamInvitationEmailLinkRequest,
    TeamInvitationPhoneLinkRequest,
)


def _params(form) -> ApiRequestParameters:
    return ApiRequestParameters(
        query=ApiParameterMap({}),
        form=ApiParameterMap(form),
    )


def test_only_exact_code_selects_code_and_preserves_raw_groups() -> None:
    code = LegacyTeamInvitationRequestParser().parse(
        _params(
            {
                "type": "code",
                "email": "0",
                "phone": "+1 23",
                "groups[]": (" 02 ", "-3", "+4", "1.0", "bad"),
            }
        )
    )

    assert isinstance(code, TeamInvitationCodeRequest)
    assert isinstance(code.email, TeamTextMissing)
    assert isinstance(code.phone, TeamTextPresent)
    assert code.requested_groups == ("02", "-3", "+4", "1.0", "bad")
    assert code.integer_group_ids == (2, -3)

    spaced = LegacyTeamInvitationRequestParser().parse(
        _params({"type": " code ", "email": "a@example.test"})
    )
    assert isinstance(spaced, TeamInvitationEmailLinkRequest)


def test_phone_has_priority_over_email_and_send() -> None:
    parsed = LegacyTeamInvitationRequestParser().parse(
        _params(
            {
                "phone": "+7 (999) 1",
                "email": "ignored@example.test",
                "send": "true",
            }
        )
    )

    assert isinstance(parsed, TeamInvitationPhoneLinkRequest)
    assert parsed.phone == "+7 (999) 1"


def test_link_email_required_uses_framework_invalid_param() -> None:
    parsed = LegacyTeamInvitationRequestParser().parse(
        _params({"phone": "0", "email": "0"})
    )

    assert isinstance(parsed, ApiParameterRejected)
    assert parsed.error.code is ApiFrameworkErrorCode.INVALID_PARAM


def test_send_conversion_matches_legacy_truth_rules() -> None:
    parser = LegacyTeamInvitationRequestParser()
    values = {
        "true": True,
        " TRUE ": True,
        "false": False,
        "0": False,
        "": False,
        "yes": True,
    }
    for raw, expected in values.items():
        parsed = parser.parse(
            _params(
                {
                    "email": "a@example.test",
                    "send": raw,
                }
            )
        )
        assert isinstance(parsed, TeamInvitationEmailLinkRequest)
        assert parsed.send is expected
