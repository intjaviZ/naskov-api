from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "NasKob API"
    API_V1_STR: str = "/v1"
    DATABASE_URL: str 
    PWA_API_KEY: str
    JWT_SECRET_KEY: str 
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()