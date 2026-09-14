from fastapi import Request

from gomazon_webasyst.composition.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container
