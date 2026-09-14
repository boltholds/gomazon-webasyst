from types import SimpleNamespace

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy import factory


def test_create_engine_uses_configured_database_url(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_engine = object()

    def fake_create_async_engine(url: str, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return fake_engine

    monkeypatch.setattr(factory, "create_async_engine", fake_create_async_engine)
    settings = Settings(database_url="mysql+asyncmy://user:pass@db/webasyst")
    assert factory.create_engine(settings) is fake_engine
    assert captured == {
        "url": "mysql+asyncmy://user:pass@db/webasyst",
        "pool_pre_ping": True,
    }


def test_create_uow_factory_builds_sessionmaker(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_session_factory = object()

    def fake_async_sessionmaker(engine, **kwargs):
        captured["engine"] = engine
        captured.update(kwargs)
        return fake_session_factory

    monkeypatch.setattr(factory, "async_sessionmaker", fake_async_sessionmaker)
    fake_engine = SimpleNamespace()
    result = factory.create_uow_factory(fake_engine)  # type: ignore[arg-type]
    assert result._session_factory is fake_session_factory
    assert captured == {"engine": fake_engine, "expire_on_commit": False}
