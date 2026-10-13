from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )
    database_url: str
    secret_key: str
    access_token_expires_minutes: int
    redis_url: str


settings = Settings()
