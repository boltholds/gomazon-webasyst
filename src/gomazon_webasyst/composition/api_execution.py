from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.api_credentials import ResolveApiAccessToken
from gomazon_webasyst.application.api_execution.composites.pipeline import ApiExecutionPipeline
from gomazon_webasyst.application.api_execution.services.activity import ApiUserActivityService
from gomazon_webasyst.application.api_execution.services.authorizer import ApiRequestAuthorizer
from gomazon_webasyst.application.api_execution.services.method_executor import ApiMethodExecutor
from gomazon_webasyst.application.ports.api_method_registry import ApiMethodRegistry
from gomazon_webasyst.application.ports.app_license import AppLicensePolicy
from gomazon_webasyst.application.ports.application_registry import ApplicationRegistry
from gomazon_webasyst.compatibility.webasyst.api.composites.response_renderer import LegacyApiResponseRenderer
from gomazon_webasyst.compatibility.webasyst.api.services.app_access import LegacyApiAppAccessService
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import LegacyApiCredentialExtractionService
from gomazon_webasyst.compatibility.webasyst.api.services.license import AllowAllAppLicensePolicy
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import LegacyApiTransportPreconditionService
from gomazon_webasyst.compatibility.webasyst.api.services.response_format import LegacyApiResponseFormatService
from gomazon_webasyst.compatibility.webasyst.api.services.target_parser import LegacyApiTargetParser
from gomazon_webasyst.composition.access_control import create_webasyst_rights_evaluator
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import SQLAlchemyAccessControlUnitOfWorkFactory
from gomazon_webasyst.infrastructure.api_execution.activity import SQLAlchemyApiUserActivityStore
from gomazon_webasyst.infrastructure.api_execution.method_registry import InMemoryApiMethodRegistry


@dataclass(slots=True, frozen=True)
class ApiExecutionComponents:
    pipeline: ApiExecutionPipeline
    method_registry: ApiMethodRegistry
    application_registry: ApplicationRegistry
    preconditions: LegacyApiTransportPreconditionService
    target_parser: LegacyApiTargetParser
    credential_extractor: LegacyApiCredentialExtractionService
    response_format_service: LegacyApiResponseFormatService
    response_renderer: LegacyApiResponseRenderer


def create_api_execution_components(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    resolve_api_access_token: ResolveApiAccessToken,
    method_registry: ApiMethodRegistry,
    application_registry: ApplicationRegistry,
    license_policy: AppLicensePolicy,
    api_enabled: bool,
    disable_message: str,
    force_https: bool,
) -> ApiExecutionComponents:
    activity = ApiUserActivityService(
        SQLAlchemyApiUserActivityStore(session_factory),
        clock=datetime.now,
    )
    app_access = LegacyApiAppAccessService(
        SQLAlchemyAccessControlUnitOfWorkFactory(session_factory),
        create_webasyst_rights_evaluator(),
    )
    authorizer = ApiRequestAuthorizer(
        application_registry=application_registry,
        app_access=app_access,
        license_policy=license_policy,
    )
    pipeline = ApiExecutionPipeline(
        resolve_access_token=resolve_api_access_token,
        activity_service=activity,
        authorizer=authorizer,
        method_registry=method_registry,
        method_executor=ApiMethodExecutor(),
    )
    return ApiExecutionComponents(
        pipeline=pipeline,
        method_registry=method_registry,
        application_registry=application_registry,
        preconditions=LegacyApiTransportPreconditionService(
            api_enabled=api_enabled,
            disable_message=disable_message,
            force_https=force_https,
        ),
        target_parser=LegacyApiTargetParser(),
        credential_extractor=LegacyApiCredentialExtractionService(),
        response_format_service=LegacyApiResponseFormatService(),
        response_renderer=LegacyApiResponseRenderer(),
    )


def create_default_api_execution_components(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    resolve_api_access_token: ResolveApiAccessToken,
    api_enabled: bool,
    disable_message: str,
    force_https: bool,
    application_registry: ApplicationRegistry,
) -> ApiExecutionComponents:
    return create_api_execution_components(
        session_factory=session_factory,
        resolve_api_access_token=resolve_api_access_token,
        method_registry=InMemoryApiMethodRegistry(),
        application_registry=application_registry,
        license_policy=AllowAllAppLicensePolicy(),
        api_enabled=api_enabled,
        disable_message=disable_message,
        force_https=force_https,
    )
