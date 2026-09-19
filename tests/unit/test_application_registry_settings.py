from pathlib import Path

from gomazon_webasyst.composition.settings import Settings


def test_webasyst_root_is_typed_path_and_reads_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "legacy-root"
    root.mkdir()
    monkeypatch.setenv("GOMAZON_WEBASYST_ROOT", str(root))

    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

    assert isinstance(settings.webasyst_root, Path)
    assert settings.webasyst_root == root


def test_webasyst_root_defaults_to_current_directory() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

    assert settings.webasyst_root == Path(".")
