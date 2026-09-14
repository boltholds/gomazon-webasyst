from contextlib import asynccontextmanager

from fastapi import FastAPI

from gomazon_webasyst.composition.container import create_container
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.presentation.http.contacts import router as contacts_router
from gomazon_webasyst.presentation.http.errors import install_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    container = create_container(resolved)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container
        try:
            yield
        finally:
            await container.close()

    app = FastAPI(title=resolved.app_name, lifespan=lifespan)
    app.include_router(contacts_router)
    install_error_handlers(app)
    return app
