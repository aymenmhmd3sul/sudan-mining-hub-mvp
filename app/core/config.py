from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sudan Mining Hub MVP"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    APP_BASE_URL: str = "http://127.0.0.1:8001"

    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "onboarding@resend.dev"

    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
