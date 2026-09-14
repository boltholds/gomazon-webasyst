from gomazon_webasyst.composition.settings import Settings


def test_default_backend_is_sqlalchemy() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert settings.database_backend == "sqlalchemy"


def test_mysql_async_url_is_accepted() -> None:
    settings = Settings(database_url="mysql+asyncmy://user:pass@db/webasyst")
    assert settings.database_url == "mysql+asyncmy://user:pass@db/webasyst"
