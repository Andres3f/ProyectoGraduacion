from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Base de datos ──────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql://optirutas:optirutas_secret@db:5432/optirutas_jalapa"
    )

    # ── JWT ────────────────────────────────────────────────────
    SECRET_KEY: str = "super-secret-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 h

    # ── App ────────────────────────────────────────────────────
    APP_NAME: str = "Optirutas Jalapa"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
