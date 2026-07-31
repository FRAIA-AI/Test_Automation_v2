"""Validated runtime configuration shared by all monitors."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Raised when a required monitoring setting is not configured."""


@dataclass(frozen=True, slots=True)
class Settings:
    base_app_url: str
    test_username: str
    test_password: str
    admin_username: str
    admin_password: str
    auth_cookie_name: str
    audio_file: Path
    audio_oracle_file: Path
    fnx_file: Path
    fnx_oracle_file: Path

    @property
    def sign_in_url(self) -> str:
        return f"{self.base_app_url.rstrip('/')}/signin"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once, allowing a local .env file but never requiring it."""

    load_dotenv()
    return Settings(
        base_app_url=os.getenv("BASE_APP_URL", "https://clinic.peoplesdoctor.ai").rstrip("/"),
        test_username=os.getenv("TEST_USERNAME", "").strip(),
        test_password=os.getenv("TEST_PASSWORD", ""),
        admin_username=os.getenv("ADMIN_USERNAME", "").strip(),
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        auth_cookie_name=os.getenv("AUTH_COOKIE_NAME", "").strip(),
        audio_file=Path(os.getenv("AUDIO_FILE_PATH", "test_data/consultation-audio.webm")),
        audio_oracle_file=Path(
            os.getenv("AUDIO_ORACLE_PATH", "test_data/consultation-audio.oracle.json")
        ),
        fnx_file=Path(
            os.getenv("FNX_FILE_PATH", "test_data/2024-12-14_CGM_P300_1_Ref.FNX")
        ),
        fnx_oracle_file=Path(os.getenv("FNX_ORACLE_PATH", "test_data/fnx.oracle.json")),
    )


def require_smoke_credentials(settings: Settings) -> None:
    missing = [
        name
        for name, value in {
            "TEST_USERNAME": settings.test_username,
            "TEST_PASSWORD": settings.test_password,
        }.items()
        if not value
    ]
    if missing:
        raise ConfigurationError(
            "Missing required smoke-monitor configuration: " + ", ".join(missing)
        )


def require_admin_credentials(settings: Settings) -> None:
    missing = [
        name
        for name, value in {
            "ADMIN_USERNAME": settings.admin_username,
            "ADMIN_PASSWORD": settings.admin_password,
        }.items()
        if not value
    ]
    if missing:
        raise ConfigurationError(
            "Missing required deep-monitor configuration: " + ", ".join(missing)
        )


def require_files(*paths: Path) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ConfigurationError("Missing required test fixture(s): " + ", ".join(missing))
