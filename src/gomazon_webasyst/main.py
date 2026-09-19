from contextlib import asynccontextmanager

from fastapi import FastAPI

from gomazon_webasyst.composition.container import create_container
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.presentation.http.contacts import router as contacts_router
from gomazon_webasyst.presentation.http.legacy_api import create_legacy_api_router
from gomazon_webasyst.presentation.http.errors import install_error_handlers


def create_app() -> FastAPI:
    return create_app_with_settings(Settings())


def create_app_with_settings(settings: Settings) -> FastAPI:
    container = create_container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container
        try:
            yield
        finally:
            await container.close()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(contacts_router)
    app.include_router(create_legacy_api_router(container.api_execution))
    install_error_handlers(app)
    return app
