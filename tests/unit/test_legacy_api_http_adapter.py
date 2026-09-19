import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gomazon_webasyst.application.api_execution.composites.results import ApiExecutionSucceeded
from gomazon_webasyst.compatibility.webasyst.api.composites.response_renderer import LegacyApiResponseRenderer
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import LegacyApiCredentialExtractionService
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import LegacyApiTransportPreconditionService
from gomazon_webasyst.compatibility.webasyst.api.services.response_format import LegacyApiResponseFormatService
from gomazon_webasyst.compatibility.webasyst.api.services.target_parser import LegacyApiTargetParser
from gomazon_webasyst.composition.api_execution import ApiExecutionComponents
from gomazon_webasyst.presentation.http.legacy_api import create_legacy_api_router


class RecordingPipeline:
    def __init__(self):
        self.requests = []

    async def __call__(self, request):
        self.requests.append(request)
        return ApiExecutionSucceeded(
            payload={"app": request.target.app_id.value, "method": request.target.method.value},
            status_code=200,
        )


def components(*, enabled=True, force_https=False):
    pipeline = RecordingPipeline()
    return ApiExecutionComponents(
        pipeline=pipeline,
        method_registry=object(),
        installed_app_directory=object(),
        preconditions=LegacyApiTransportPreconditionService(
            api_enabled=enabled,
            disable_message="maintenance",
            force_https=force_https,
        ),
        target_parser=LegacyApiTargetParser(),
        credential_extractor=LegacyApiCredentialExtractionService(),
        response_format_service=LegacyApiResponseFormatService(),
        response_renderer=LegacyApiResponseRenderer(),
    )


def client_for(parts):
    app = FastAPI()
    app.include_router(create_legacy_api_router(parts))
    return TestClient(app), parts.pipeline


def test_three_route_forms_normalize_to_same_method_target() -> None:
    parts = components()
    client, pipeline = client_for(parts)
    headers = {"Authorization": "Bearer abc"}

    assert client.get("/api.php?app=shop&method=ping", headers=headers).status_code == 200
    assert client.get("/api.php/shop/ping", headers=headers).status_code == 200
    assert client.get("/api.php/shop.ping", headers=headers).status_code == 200

    assert [(r.target.app_id.value, r.target.method.value) for r in pipeline.requests] == [
        ("shop", "ping"), ("shop", "ping"), ("shop", "ping")
    ]


def test_missing_token_returns_legacy_token_required_error() -> None:
    client, _ = client_for(components())
    response = client.get("/api.php?app=shop&method=ping")
    assert response.status_code == 400
    assert response.json()["error"] == "token_required"


def test_reserved_auth_endpoint_never_calls_pipeline() -> None:
    parts = components()
    client, pipeline = client_for(parts)
    response = client.get("/api.php/auth")
    assert response.status_code == 404
    assert pipeline.requests == []


def test_api_disabled_is_legacy_404_before_pipeline() -> None:
    parts = components(enabled=False)
    client, pipeline = client_for(parts)
    response = client.get("/api.php/shop/ping", headers={"Authorization": "Bearer abc"})
    assert response.status_code == 404
    assert response.json()["error"] == "disabled"
    assert pipeline.requests == []


def test_https_precondition_redirects_before_pipeline() -> None:
    parts = components(force_https=True)
    client, pipeline = client_for(parts)
    response = client.get(
        "/api.php/shop/ping?access_token=abc",
        follow_redirects=False,
    )
    assert response.status_code == 301
    assert response.headers["location"].startswith("https://")
    assert pipeline.requests == []


def test_invalid_explicit_format_uses_legacy_200_error_response() -> None:
    client, pipeline = client_for(components())
    response = client.get(
        "/api.php/shop/ping?access_token=abc&format=yaml",
    )
    assert response.status_code == 200
    assert response.json()["error"] == "invalid_request"
    assert pipeline.requests == []


def test_xml_format_is_rendered_by_compatibility_renderer() -> None:
    client, _ = client_for(components())
    response = client.get(
        "/api.php/shop/ping?access_token=abc&format=xml",
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/xml")
    assert "<app>shop</app>" in response.text
