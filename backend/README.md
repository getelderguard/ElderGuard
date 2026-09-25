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
FAKE_PROVIDERS=1 DEV_ALLOWED_PHONES=+14155550142 uv run uvicorn app.main:create_app --factory --reload
```

In dev auth mode, `/v1` routes take `X-Dev-Uid` and `X-Dev-Phone` headers instead of a Firebase token. The seeded senior for the number above has uid `dev-0142`. Prod refuses dev auth, the memory store, and fakes at startup.

Tests:

```bash
uv run pytest                      # unit and API tests, no network
uv run ruff check . && uv run ruff format --check .
```

Firestore repository tests run only against the emulator (needs JDK 21 and firebase-tools):

```bash
cd ../infra && firebase emulators:exec --only firestore --project demo-elderguard \
  "cd ../backend && FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 GCP_PROJECT=demo-elderguard uv run pytest tests/test_firestore_repos.py"
```

Offline evaluation of the scorer over the fixture corpus (see `eval/README.md`):

```bash
uv run python eval/run.py --gate
```

## Layout

- `app/settings.py` every secret comes from the environment
- `app/providers/` pluggable AI providers behind four protocols, plus deterministic fakes
- `app/scoring/` rubric, trip-wire, evidence gate, rolling scorer with hysteresis
- `app/telephony/` TwiML, mulaw codec
- `app/twilio/` voice webhooks and the media-stream WebSocket
- `app/sessions/` session and account models, in-memory store and account repo, account service
- `app/persistence/` Firestore back ends for sessions, accounts, usage, and the config overlay; the cached config service
- `app/security/` phone hashing, stream tokens, Twilio signatures, Firebase auth, scheduler OIDC
- `app/api/` `/v1` accounts, guardians, devices, sessions; `/internal` scheduler targets; `/admin` staff reads
- `app/notify/` push decisions and the FCM sender; payloads never carry call content
- `config/` provider routing and feature-flag defaults; Firestore `config/*` overlays them at runtime
- `eval/` fixture corpus and the offline scoring harness
