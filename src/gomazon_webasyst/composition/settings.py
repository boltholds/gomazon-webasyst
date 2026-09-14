from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="GOMAZON_", extra="ignore")

    app_name: str = "gomazon-webasyst"
    database_backend: Literal["sqlalchemy"] = "sqlalchemy"
    database_url: str
