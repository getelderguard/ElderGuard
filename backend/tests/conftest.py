from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from twilio.request_validator import RequestValidator

from app.main import create_app
from app.settings import Settings

PUBLIC_BASE = "https://api.example.test"
TWILIO_TOKEN = "test-twilio-auth-token"
ENROLLED = "+14155550142"
STRANGER = "+12125550199"


def make_settings(**overrides) -> Settings:
    base = dict(
        env="test",
        public_base_url=PUBLIC_BASE,
        twilio_auth_token=SecretStr(TWILIO_TOKEN),
        twilio_guardian_number="+14155550100",
        phone_hash_pepper=SecretStr("test-pepper"),
        stream_token_secret=SecretStr("test-stream-secret"),
        fake_providers="1",
        dev_allowed_phones=ENROLLED,
        scoring_speed_factor=0.02,
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def signed_headers(path: str, params: dict[str, str]) -> dict[str, str]:
    sig = RequestValidator(TWILIO_TOKEN).compute_signature(PUBLIC_BASE + path, params)
    return {"X-Twilio-Signature": sig}


def twilio_post(client: TestClient, path: str, params: dict[str, str], *, sign: bool = True):
    headers = signed_headers(path, params) if sign else {}
    return client.post(path, data=params, headers=headers)
