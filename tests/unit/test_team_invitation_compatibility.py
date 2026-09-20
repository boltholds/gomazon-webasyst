from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.team.invitation import (
    LegacyTeamInvitationLinkBuilder,
    LegacyTeamInvitationRequestParser,
    LegacyTeamInvitationValidator,
)
from gomazon_webasyst.contracts.enums import TeamInvitationMode


def _params(form):
    return ApiRequestParameters(
        query=ApiParameterMap({}),
        form=ApiParameterMap(form),
    )


def test_invite_parser_uses_post_only_and_preserves_repeated_groups() -> None:
    request = LegacyTeamInvitationRequestParser().parse(
        _params(
            {
                "type": "code",
                "email": "a@example.test",
                "phone": "",
                "groups[]": (" 2 ", "-3", "1.0", "bad"),
                "send": "true",
            }
        )
    )
    assert request.mode is TeamInvitationMode.CODE
    assert request.group_ids == (2, -3)
    assert request.send is True


def test_send_uses_legacy_php_boolean_rules() -> None:
    parser = LegacyTeamInvitationRequestParser()
    assert parser.parse(_params({"send": "false"})).send is False
    assert parser.parse(_params({"send": "0"})).send is False
    assert parser.parse(_params({"send": "yes"})).send is True


def test_invitation_validator_pins_common_email_and_exact_phone_rules() -> None:
    validator = LegacyTeamInvitationValidator()
    assert validator.email_errors("") == ("email_required",)
    assert validator.email_errors("bad") == ("email_invalid",)
    assert validator.email_errors("ok@example.test") == ()
    assert validator.phone_errors("") == ("phone_required",)
    assert validator.phone_errors("+31 (20) 123-4567") == ()
    assert validator.phone_errors("123abc") == ("phone_invalid",)


def test_invitation_link_builder_encodes_legacy_token_symbols() -> None:
    url = LegacyTeamInvitationLinkBuilder(
        "https://example.test/"
    ).build("A(~*)")
    assert url == (
        "https://example.test/link.php/A%28%7E%2A%29/"
    )
