import json
from pathlib import Path

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    # NoDecode stops pydantic-settings JSON-parsing the env var before the
    # validator below sees it, so a plain comma-separated string is accepted.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # Optional: raises GitHub's rate limit from 60 to 5000 requests per hour,
    # which a first LeetCode import needs.
    github_token: str | None = None
    # Optional: enables the AI daily plan. Free key from console.groq.com/keys.
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # The timezone every calendar day in the app is measured in — streaks,
    # "this week", which revisions are due. Not a display setting: it decides
    # which day a submission belongs to, so changing it moves history.
    #
    # One zone for the whole app rather than one per user. Solvix is built for
    # one person's placement prep, and a per-user zone would add a column and a
    # settings screen to make no difference to anybody currently using it.
    timezone: str = "Asia/Kolkata"

    # How many proxies sit in front of the app. Render terminates TLS and adds
    # one hop; put a CDN in front as well and this becomes 2. It decides which
    # X-Forwarded-For entry is believed, so getting it too high trusts an
    # address the client wrote, and too low lumps every caller together.
    trusted_proxy_hops: int = 1

    # Mail. With no host configured, messages are printed to the server log
    # instead of sent, so email verification works in development without an
    # SMTP account. Set these to send for real.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True
    mail_from: str = "Solvix <no-reply@solvix.local>"

    # Where an email should send the reader back to.
    app_url: str = "http://localhost:5173"
    # Shared secret for the scheduled-job endpoint. Unset means the endpoint
    # refuses every call rather than running unauthenticated — a job that
    # rewrites reminders and sends mail must not be open to the internet
    # merely because nobody configured it.
    cron_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        # Hosting dashboards only accept plain strings, so a JSON list is
        # awkward to type into one. Accept "a,b" as well as '["a","b"]'.
        if isinstance(value, str):
            if value.lstrip().startswith("["):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def mail_configured(self) -> bool:
        return bool(self.smtp_host)

    # Anchored to backend/ so the app and alembic load the same .env no matter
    # which directory they are invoked from.
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")


settings = Settings()
