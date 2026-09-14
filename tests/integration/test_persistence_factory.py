import pytest

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.factory import create_engine


@pytest.mark.asyncio
async def test_mysql_async_dialect_is_selected_without_connecting() -> None:
    pytest.importorskip("asyncmy")
    engine = create_engine(
        Settings(database_url="mysql+asyncmy://user:pass@localhost/webasyst")
    )
    try:
        assert engine.dialect.name == "mysql"
        assert engine.dialect.is_async is True
    finally:
        await engine.dispose()
