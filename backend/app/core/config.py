from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url: str | None = None
    database_url_unpooled: str | None = None
    static_dir: Path | None = None
    jwt_secret: SecretStr | None = None
    cookie_secure: bool = True
    auth_rate_limit: int = Field(default=20, ge=1, le=1000)
    app_name: str = "MASTERLY API"
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or "*" in value
            ):
                raise ValueError(
                    "CORS requires explicit HTTP(S) origins without paths or wildcards"
                )
        return values

    @model_validator(mode="after")
    def local_only_insecure_cookie(self):
        if not self.cookie_secure and any(
            urlsplit(origin).hostname not in {"localhost", "127.0.0.1", "::1"}
            for origin in self.cors_origins
        ):
            raise ValueError("COOKIE_SECURE=false is allowed only for loopback development origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
