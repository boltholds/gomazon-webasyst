from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import (
    ApiTransportAccepted,
    ApiTransportDisabled,
    ApiHttpsRequired,
    LegacyApiTransportPreconditionService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.target_parser import (
    ApiTargetMalformed,
    ApiTargetParsed,
    ApiTargetReservedEndpoint,
    LegacyApiTargetParser,
)


def test_source_backed_dispatch_forms_and_reserved_paths() -> None:
    parser = LegacyApiTargetParser()
    assert isinstance(parser.parse("api.php", ApiParameterMap({"app": "shop", "method": "ping"})), ApiTargetParsed)
    assert isinstance(parser.parse("api.php/shop/ping", ApiParameterMap({})), ApiTargetParsed)
    assert isinstance(parser.parse("api.php/shop.ping", ApiParameterMap({})), ApiTargetParsed)
    assert isinstance(parser.parse("api.php/auth", ApiParameterMap({})), ApiTargetReservedEndpoint)
    assert isinstance(parser.parse("broken", ApiParameterMap({})), ApiTargetMalformed)


def test_source_backed_api_disable_and_https_preconditions() -> None:
    disabled = LegacyApiTransportPreconditionService(
        api_enabled=False,
        disable_message="maintenance",
        force_https=False,
    ).evaluate(is_https=False)
    assert isinstance(disabled, ApiTransportDisabled)
    assert disabled.message == "maintenance"

    redirect = LegacyApiTransportPreconditionService(
        api_enabled=True,
        disable_message="",
        force_https=True,
    ).evaluate(is_https=False)
    assert isinstance(redirect, ApiHttpsRequired)

    accepted = LegacyApiTransportPreconditionService(
        api_enabled=True,
        disable_message="",
        force_https=True,
    ).evaluate(is_https=True)
    assert isinstance(accepted, ApiTransportAccepted)
