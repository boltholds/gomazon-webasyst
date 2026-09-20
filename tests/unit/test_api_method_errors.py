from gomazon_webasyst.compatibility.webasyst.api.services.error_mapper import (
    LegacyApiErrorMapper,
)
from gomazon_webasyst.contracts.api_execution import (
    ApiApplicationErrorCode,
    ApiFrameworkError,
    ApiMethodError,
    ApiMethodRejected,
)
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


def test_method_error_code_is_open_and_maps_to_legacy_payload() -> None:
    error = ApiMethodError(
        code=ApiApplicationErrorCode("user_in_team"),
        description="Already in our team!",
        http_status=409,
        details={"contact_id": 7},
    )
    result = ApiMethodRejected(error=error)

    assert result.error.code.value == "user_in_team"
    assert LegacyApiErrorMapper().payload(result.error) == {
        "error": "user_in_team",
        "contact_id": 7,
        "error_description": "Already in our team!",
    }


def test_framework_error_enum_remains_closed_and_supported() -> None:
    error = ApiFrameworkError(
        code=ApiFrameworkErrorCode.INVALID_PARAM,
        description="Missing",
        http_status=400,
        details={},
    )

    assert LegacyApiErrorMapper().payload(error) == {
        "error": "invalid_param",
        "error_description": "Missing",
    }


def test_raw_known_code_prefers_framework_error_model() -> None:
    from pydantic import TypeAdapter

    from gomazon_webasyst.contracts.api_execution import ApiExecutionResult

    value = TypeAdapter(ApiExecutionResult).validate_python(
        {
            "kind": "rejected",
            "error": {
                "code": "invalid_request",
                "description": "bad request",
                "http_status": 400,
                "details": {},
            },
        }
    )

    assert isinstance(value.error, ApiFrameworkError)
    assert value.error.code is ApiFrameworkErrorCode.INVALID_REQUEST


def test_raw_unknown_code_becomes_application_error() -> None:
    from pydantic import TypeAdapter

    from gomazon_webasyst.contracts.api_execution import (
        ApiExecutionResult,
    )

    value = TypeAdapter(ApiExecutionResult).validate_python(
        {
            "kind": "rejected",
            "error": {
                "code": "user_in_team",
                "description": "Already in our team!",
                "http_status": 409,
                "details": {"contact_id": 7},
            },
        }
    )

    assert isinstance(value.error, ApiMethodError)
    assert value.error.code.value == "user_in_team"
