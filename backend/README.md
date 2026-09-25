# ElderGuard backend

FastAPI service that answers the Guardian Line, streams the merged call audio to a transcription provider, scores the rolling transcript with an LLM, and publishes live tiers for the app.

## Run locally

```bash
cd backend
uv sync
cp ../.env.example ../.env   # fill in real values, never commit .env
uv run uvicorn app.main:create_app --factory --reload
```

With no credentials at all:

```bash
FAKE_PROVIDERS=1 uv run uvicorn app.main:create_app --factory --reload
```

Tests:

```bash
uv run pytest
```

## Layout

- `app/settings.py` every secret comes from the environment
- `app/providers/` pluggable AI providers behind four protocols, plus deterministic fakes
- `app/scoring/` rubric, trip-wire, evidence gate, rolling scorer with hysteresis
- `app/telephony/` TwiML, mulaw codec
- `app/twilio/` voice webhooks and the media-stream WebSocket
- `app/sessions/` session and account models, in-memory store (Firestore in M1)
- `config/` provider routing and feature-flag defaults
