from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///:memory:"
    secret_key: str = "dev-secret-change-in-production"
    environment: str = "development"
    log_level: str = "INFO"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8  # 8 hours

    # Session cookies. `secure` was hardcoded False; outside development the
    # cookie must not travel over plain HTTP (ADR 0009).
    cookie_secure: bool | None = None

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def session_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return not self.is_development


settings = Settings()
