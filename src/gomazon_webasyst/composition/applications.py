from gomazon_webasyst.application.application_registry import (
    ApplicationCatalog,
    InstallationManifest,
    StaticApplicationRegistry,
)


def create_default_application_registry() -> StaticApplicationRegistry:
    return StaticApplicationRegistry(
        ApplicationCatalog(()),
        InstallationManifest(()),
    )
