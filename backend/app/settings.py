"""Runtime configuration. Every secret is read from the environment or a gitignored .env."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_DEV_PEPPER = "dev-only-pepper-change-me"
_DEV_STREAM_SECRET = "dev-only-stream-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "dev"
    log_level: str = "INFO"

    # Public HTTPS origin Twilio calls back to (ngrok in M0, Cloud Run later).
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = ""

    anthropic_api_key: SecretStr | None = None
    stt_api_key: SecretStr | None = None

    twilio_account_sid: str | None = None
    twilio_auth_token: SecretStr | None = None
    twilio_guardian_number: str | None = None

    phone_hash_pepper: SecretStr = SecretStr(_DEV_PEPPER)
    stream_token_secret: SecretStr = SecretStr(_DEV_STREAM_SECRET)

    # "" = real providers, "1" = deterministic fakes, "fail" = fakes that always fail.
    fake_providers: str = ""
    # Comma-separated E.164 numbers that count as enrolled accounts before Firestore exists.
    dev_allowed_phones: str = ""

    providers_config_path: Path = _CONFIG_DIR / "providers.default.yaml"
    flags_config_path: Path = _CONFIG_DIR / "flags.default.yaml"

    # Scales every scoring time constant. Tests set this small so cadence rules run fast.
    scoring_speed_factor: float = 1.0

    @cached_property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @cached_property
    def dev_allowed_phone_list(self) -> list[str]:
        return [p.strip() for p in self.dev_allowed_phones.split(",") if p.strip()]

    @property
    def fakes_enabled(self) -> bool:
        return self.fake_providers.strip().lower() in {"1", "true", "yes", "fail"}

    @property
    def fakes_fail(self) -> bool:
        return self.fake_providers.strip().lower() == "fail"

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"

    def insecure_defaults_in_use(self) -> list[str]:
        problems: list[str] = []
        if self.phone_hash_pepper.get_secret_value() == _DEV_PEPPER:
            problems.append("PHONE_HASH_PEPPER")
        if self.stream_token_secret.get_secret_value() == _DEV_STREAM_SECRET:
            problems.append("STREAM_TOKEN_SECRET")
        return problems
