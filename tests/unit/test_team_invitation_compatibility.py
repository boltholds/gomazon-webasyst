from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.api.services.parameter_reader import (
    ApiParameterRejected,
)
from gomazon_webasyst.compatibility.webasyst.team.invitation import (
    LegacyTeamInvitationLinkBuilder,
    LegacyTeamInvitationRequestParser,
    LegacyTeamInvitationValidator,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationCodeRequest,
    TeamInvitationEmailLinkRequest,
)


def _params(form):
    return ApiRequestParameters(
        query=ApiParameterMap({}),
        form=ApiParameterMap(form),
    )


def test_invite_parser_preserves_code_groups_and_send_semantics() -> None:
    request = LegacyTeamInvitationRequestParser().parse(
        _params(
            {
                "type": "code",
                "email": "a@example.test",
                "groups[]": (" 2 ", "-3", "1.0", "bad"),
            }
        )
    )
    assert isinstance(request, TeamInvitationCodeRequest)
    assert request.requested_groups == ("2", "-3", "1.0", "bad")
    assert request.integer_group_ids == (2, -3)

    parser = LegacyTeamInvitationRequestParser()
    for raw, expected in (("false", False), ("0", False), ("yes", True)):
        parsed = parser.parse(
            _params({"email": "a@example.test", "send": raw})
        )
        assert isinstance(parsed, TeamInvitationEmailLinkRequest)
        assert parsed.send is expected


def test_link_email_required_is_framework_rejection() -> None:
    parsed = LegacyTeamInvitationRequestParser().parse(_params({}))
    assert isinstance(parsed, ApiParameterRejected)
    assert parsed.error.code.value == "invalid_param"


def test_invitation_validator_and_link_builder() -> None:
    validator = LegacyTeamInvitationValidator()
    assert validator.email_errors("") == ("email_required",)
    assert validator.email_errors("bad") == ("email_invalid",)
    assert validator.email_errors("ok@example.test") == ()
    assert validator.phone_errors("+31 (20) 123-4567") == ()
    assert validator.phone_errors("123abc") == ("phone_invalid",)

    assert LegacyTeamInvitationLinkBuilder(
        "https://example.test/"
    ).build("A(~*)") == "https://example.test/link.php/A%28%7E%2A%29/"


def test_email_validator_preserves_legacy_rfc_and_idna_cases() -> None:
    validator = LegacyTeamInvitationValidator()

    assert validator.email_errors('"foo@bar"@example.com') == ()
    assert validator.email_errors("user@[127.0.0.1]") == ()
    assert validator.email_errors("user@[IPv6:2001:db8::1]") == ()
    assert validator.email_errors("user@пример.рф") == ()
    assert validator.email_errors("a..b@example.com") == ("email_invalid",)
    assert validator.email_errors("<script@example.com") == ("email_invalid",)


def test_invitation_link_builder_decodes_idna_root_like_webasyst() -> None:
    assert LegacyTeamInvitationLinkBuilder(
        "https://xn--e1afmkfd.xn--p1ai/"
    ).build("token") == "https://пример.рф/link.php/token/"


def test_wa_is_int_uses_ascii_digits_like_legacy() -> None:
    parsed = LegacyTeamInvitationRequestParser().parse(
        _params(
            {
                "type": "code",
                "groups[]": ("2", "٢", "-٣", "-3"),
            }
        )
    )

    assert isinstance(parsed, TeamInvitationCodeRequest)
    assert parsed.requested_groups == ("2", "٢", "-٣", "-3")
    assert parsed.integer_group_ids == (2, -3)
