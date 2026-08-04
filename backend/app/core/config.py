from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Optional: raises GitHub's rate limit from 60 to 5000 requests per hour,
    # which a first LeetCode import needs.
    github_token: str | None = None
    # Optional: enables the AI daily plan. Free key from console.groq.com/keys.
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Mail. With no host configured, messages are printed to the server log
    # instead of sent, so email verification works in development without an
    # SMTP account. Set these to send for real.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True
    mail_from: str = "Solvix <no-reply@solvix.local>"

    @property
    def mail_configured(self) -> bool:
        return bool(self.smtp_host)

    # Anchored to backend/ so the app and alembic load the same .env no matter
    # which directory they are invoked from.
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")


settings = Settings()
