from types import SimpleNamespace

from gomazon_webasyst.composition.container import Container
from gomazon_webasyst.composition.settings import Settings


async def noop_close():
    return None


def test_container_exposes_auth_session_use_cases_as_first_class_dependencies():
    engine = SimpleNamespace(dispose=noop_close)
    container = Container(
        settings=Settings(database_url="sqlite+aiosqlite:///:memory:"),
        engine=engine,
        get_contact=object(),
        create_contact=object(),
        update_contact=object(),
        authenticate_backend_password=object(),
        resolve_backend_session=object(),
        logout_backend_session=object(),
    )

    assert container.authenticate_backend_password is not None
    assert container.resolve_backend_session is not None
    assert container.logout_backend_session is not None
