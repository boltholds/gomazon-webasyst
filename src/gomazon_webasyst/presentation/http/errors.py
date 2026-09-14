from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gomazon_webasyst.application.errors import ContactNotFound


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ContactNotFound)
    async def handle_contact_not_found(
        request: Request,
        exc: ContactNotFound,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
