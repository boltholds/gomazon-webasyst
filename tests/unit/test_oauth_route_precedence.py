from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gomazon_webasyst.application.api_execution.composites.results import (
    ApiExecutionSucceeded,
)
from gomazon_webasyst.compatibility.webasyst.api.composites.response_renderer import (
    LegacyApiResponseRenderer,
)
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import (
    LegacyApiCredentialExtractionService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import (
    LegacyApiTransportPreconditionService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.response_format import (
    LegacyApiResponseFormatService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.target_parser import (
    LegacyApiTargetParser,
)
from gomazon_webasyst.composition.api_execution import ApiExecutionComponents
from gomazon_webasyst.presentation.http.legacy_api import create_legacy_api_router
from gomazon_webasyst.presentation.http.legacy_oauth import create_legacy_oauth_router

from tests.unit.test_legacy_oauth_token_revoke_http import parts as oauth_parts


class RecordingPipeline:
    def __init__(self):
        self.requests = []

    async def __call__(self, request):
        self.requests.append(request)
        return ApiExecutionSucceeded(payload={"unexpected": True})


def api_parts():
    pipeline = RecordingPipeline()
    return ApiExecutionComponents(
        pipeline=pipeline,
        method_registry=object(),
        installed_application_catalog=object(),
        preconditions=LegacyApiTransportPreconditionService(
            api_enabled=True,
            disable_message="",
            force_https=False,
        ),
        target_parser=LegacyApiTargetParser(),
        credential_extractor=LegacyApiCredentialExtractionService(),
        response_format_service=LegacyApiResponseFormatService(),
        response_renderer=LegacyApiResponseRenderer(),
    )


def test_oauth_static_routes_precede_generic_api_catch_all() -> None:
    oauth = oauth_parts()
    api = api_parts()
    app = FastAPI()
    app.include_router(create_legacy_oauth_router(oauth))
    app.include_router(create_legacy_api_router(api))

    client = TestClient(app)
    assert client.get("/api.php/token").status_code == 200
    assert client.get("/api.php/revoke").status_code == 400
    assert client.post(
        "/api.php/auth?response_type=code&redirect_uri=https://client/cb&client_name=Demo",
        data={"cancel": "1"},
        follow_redirects=False,
    ).status_code == 302
    assert api.pipeline.requests == []


def test_main_mounts_oauth_router_before_generic_legacy_api_router() -> None:
    source = Path("src/gomazon_webasyst/main.py").read_text()
    oauth = source.index("create_legacy_oauth_router(container.oauth_authorization)")
    generic = source.index("create_legacy_api_router(container.api_execution)")
    assert oauth < generic
