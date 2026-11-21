from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sudan Mining Hub MVP"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    APP_BASE_URL: str = "http://127.0.0.1:8001"
    VAPID_PUBLIC_KEY: str | None = None
    VAPID_PRIVATE_KEY: str | None = None
    VAPID_CLAIMS_EMAIL: str = "mailto:notifications@sudanmininghub.com"

    BREVO_API_KEY: str | None = None
    SENDER_EMAIL: str = "notifications@sudanmininghub.com"
    SENDER_NAME: str = "Sudan Mining Hub"

    # Listing image storage. Switch to "s3" only after Neon credentials
    # and the branch-specific endpoint have been configured on the service.
    LISTING_STORAGE_BACKEND: str = "local"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_ENDPOINT_URL_S3: str | None = None
    AWS_REGION: str | None = None
    NEON_STORAGE_BUCKET: str | None = None

    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
