from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "NasKob API"
    API_V1_STR: str = "/v1"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:0618@localhost:5432/naskob_bd"
    PWA_API_KEY: str = "aSqiDA7E0XyW8TSTVxvYaCo7OxvHbPR1qfEe9Qp4e2I"
    JWT_SECRET_KEY: str = "OYKAXKsU2x4wC3khz1x2Jgjxcu5VaOr4TRn8W33RYkd"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"


settings = Settings()
