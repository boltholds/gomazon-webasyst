from pathlib import Path
from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="GOMAZON_", extra="ignore")

    app_name: str = "gomazon-webasyst"
    database_backend: Literal["sqlalchemy"] = "sqlalchemy"
    database_url: str
    webasyst_root: Path = Path(".")
    session_state_provider: str = "memory"
    backend_session_cookie_name: str = "gomazon_session"
    persistent_auth_cookie_name: str = "auth_token"
    backend_auth_cookie_secure: bool = False
    persistent_login_enabled: bool = True
    api_enabled: bool = True
    api_disable_message: str = ""
    api_force_https: bool = False
    webasyst_public_root_url: str = "http://localhost/"
    webasyst_server_timezone: str = "UTC"
