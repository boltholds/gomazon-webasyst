from gomazon_webasyst.composition.settings import Settings


def test_default_backend_is_sqlalchemy() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert settings.database_backend == "sqlalchemy"


def test_mysql_async_url_is_accepted() -> None:
    settings = Settings(database_url="mysql+asyncmy://user:pass@db/webasyst")
    assert settings.database_url == "mysql+asyncmy://user:pass@db/webasyst"


def test_default_session_state_provider_is_memory() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

    assert settings.session_state_provider == "memory"


def test_custom_session_state_provider_name_is_accepted() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        session_state_provider="redis",
    )

    assert settings.session_state_provider == "redis"
