# ElderGuard architecture

This document is the contract between the backend, the infrastructure scripts, the mobile app, and the docs. When something here changes, the code changes in the same commit.

Status: M1 in progress. Sections marked *(pending spike)* are filled in from the carrier spike and the real-call test in `docs/M0-REAL-CALL.md`.

## System shape

```
 senior's phone ──(merge)──► Twilio Guardian Line ──► Cloud Run: elderguard-api (FastAPI, 1 instance)
                                                          │  WS /twilio/media  ← Twilio Media Streams (mulaw 8 kHz)
                                                          │  streaming STT (Deepgram, pluggable)
                                                          │  rolling LLM scoring (Anthropic, pluggable)
                                                          ▼
 Expo app ◄── Firestore sessions/{id} (onSnapshot) ◄──── FirestoreSessionStore
          ◄── FCM push on tier change  ◄──────────────── notify/fcm.py
 Cloud Scheduler ──OIDC──► POST /internal/sweep (1 min), POST /internal/rollup (daily)
 Billing budget ──Pub/Sub──► budget-killswitch function ──► config/providers.limits.kill_switch = true
                                                         └─► Twilio number voice URL → fallback TwiML Bin
```

One GCP project holds Cloud Run, Firestore (nam5), Firebase Auth (phone), FCM, Secret Manager, and one private GCS bucket. DNS and the public website are on Cloudflare in a separate repo. The API hostname (`api.getelderguard.org`) is a Cloudflare DNS record pointing at the Cloud Run domain mapping; `infra/bootstrap.sh` prints the target instead of creating the record.

## Environment variables

Every variable has a placeholder in `.env.example`. Secrets are mounted from Secret Manager in Cloud Run and never appear in `cloudrun.yaml` as literals.

| Variable | Secret | Default | Meaning |
|---|---|---|---|
| `ENV` | no | `dev` | `dev`, `test`, or `prod`. Prod refuses default secrets and disables dev auth. |
| `LOG_LEVEL` | no | `INFO` | Transcript and phone fields are redacted at any level above DEBUG. |
| `PUBLIC_BASE_URL` | no | `http://localhost:8000` | Exact public origin Twilio calls. Signature validation uses it. |
| `CORS_ORIGINS` | no | empty | Comma-separated allow-list. Empty means no CORS middleware. |
| `GCP_PROJECT` | no | empty | GCP and Firebase project id. Required when `STORE=firestore`, `AUTH_MODE=firebase`, or `NOTIFY=fcm`. |
| `STORE` | no | `memory` | `memory` or `firestore`. |
| `AUTH_MODE` | no | `dev` | `firebase` verifies Firebase ID tokens. `dev` accepts `X-Dev-Uid` and `X-Dev-Phone` headers and is refused in prod. |
| `NOTIFY` | no | `log` | `log` or `fcm`. |
| `SCHEDULER_SERVICE_ACCOUNT` | no | empty | Service-account email allowed to call `/internal/*` with a Google OIDC token. Empty disables those routes. |
| `CONFIG_CACHE_SECONDS` | no | `30` | How long the Firestore config overlay (providers, limits, flags, kill switch) is cached. |
| `ANTHROPIC_API_KEY` | yes | none | Scorer and message analyzer. |
| `STT_API_KEY` | yes | none | Streaming transcriber (Deepgram at launch). |
| `TWILIO_ACCOUNT_SID` | no | none | |
| `TWILIO_AUTH_TOKEN` | yes | none | Webhook signature validation. Missing token means webhooks return 503. |
| `TWILIO_GUARDIAN_NUMBER` | no | none | The Guardian Line, E.164. |
| `PHONE_HASH_PEPPER` | yes | dev default | HMAC pepper for phone hashes. Rotating it orphans every `phone_index` row; see `docs/RUNBOOK.md`. |
| `STREAM_TOKEN_SECRET` | yes | dev default | HMAC secret for media-stream tokens. Safe to rotate between calls. |
| `SENTRY_DSN` | yes | empty | Optional. |
| `FAKE_PROVIDERS` | no | empty | `1` runs deterministic fakes with no credentials; `fail` makes them fail. |
| `DEV_ALLOWED_PHONES` | no | empty | Memory-store enrolment list for local runs. Ignored when `STORE=firestore`. |
| `SCORING_SPEED_FACTOR` | no | `1.0` | Test-only time scaling. |
| `FIRESTORE_EMULATOR_HOST` | no | unset | Standard Google variable; the Firestore client honours it. |

## Firestore collections

Deny-by-default rules in `infra/firestore.rules`. Clients can read only what is listed under "client read". Everything else is server-only through the backend service account.

| Collection | Document | Client read | Client write |
|---|---|---|---|
| `accounts/{account_id}` | `account_id` equals the senior's Firebase uid. `senior {uid, display_name, nickname, phone_last4, consent_version, consent_at, carrier_capability, caller_id_visible}`, `guardians [{uid, name, relationship, phone_last4, linked_at, active_at}]`, `guardian_uids [uid]`, `watch_list [str]`, `settings {announcement, spoken_takeover, alert_guardian}`, `created_at`, `updated_at` | senior, and any uid in `guardian_uids` | none |
| `phone_index/{phone_hash}` | `{account_id, role: senior or guardian, uid}` | none | none |
| `guardian_invites/{invite_id}` | `{account_id, phone_hash, name, relationship, created_at, expires_at, claimed_at, claimed_uid}` | none | none |
| `sessions/{session_id}` | Every field of `app.sessions.models.Session`, plus `expire_at` (30 days after `created_at`, Firestore TTL field). `transcript_stored` is always `false`. | senior and active guardians of `account_id` | none |
| `devices/{uid}` | `{fcm_token, platform, app_version, updated_at}` | owner | owner, schema-checked |
| `usage_events/{auto}` | `app.providers.metrics.UsageEvent` plus `expire_at` (90 days) | none | none |
| `usage_monthly/{YYYY-MM}` | `{total_cost_usd, by_provider, by_capability, sessions, minutes, active_accounts, computed_at}` | none (served by `/admin/usage`) | none |
| `config/providers`, `config/flags` | Overlay documents merged over `backend/config/*.default.yaml` | none | none |
| `config_history/{auto}` | `{doc, before, after, actor, at}` | none | none |
| `show_checks/{auto}` | M4. Metadata only. | none | none |

Phone numbers are never stored in the clear. `phone_last4` is the only human-readable fragment.

### Composite indexes (`infra/firestore.indexes.json`)

Derived from the queries in `app/persistence/firestore.py`. A range filter without an explicit `order_by` sorts ascending, so those indexes are ascending.

- `sessions`: `call_sid` asc, `created_at` desc (`get_by_call_sid`)
- `sessions`: `phone_hash` asc, `state` asc, `expires_at` desc (`find_pending_intent`)
- `sessions`: `account_id` asc, `initiated_by` asc, `created_at` asc (`minutes_today`)
- `sessions`: `phone_hash` asc, `created_at` asc (`inbound_count_since`)
- `sessions`: `state` asc, `expires_at` asc (`expire_stale`)
- `sessions`: `state` asc, `created_at` asc (`abandon_stale`)
- `sessions`: `account_id` asc, `created_at` desc (`recent_for_account`)
- `guardian_invites`: `phone_hash` asc, `claimed_at` asc, `expires_at` desc (`open_invite_for_phone`)
- `usage_events`: single-field `ts` only (`events_between`)

The emulator does not enforce composite indexes, so a missing one only shows up in production as a `FAILED_PRECONDITION` with a link to create it. Keep this list and `infra/firestore.indexes.json` in sync.

## HTTP surface

| Route | Auth | Rate limit | Notes |
|---|---|---|---|
| `GET /health` | none | none | Dependency-free. Uptime check target. |
| `GET /ready` | none | none | Store, auth mode, provider routes, kill switch. |
| `POST /twilio/voice/inbound`, `/reconnect`, `/status`, `/stream-status` | Twilio signature | none | |
| `WS /twilio/media` | HMAC token in stream parameters | none | |
| `POST /v1/accounts/me` | user | 3/min | Enroll. Phone comes from the verified token, never the body. Body: `display_name`, `nickname`, `consent_version`, `watch_list`. |
| `GET /v1/accounts/me`, `PATCH /v1/accounts/me` | user | 30/min | PATCH allows `nickname`, `watch_list`, `settings`, `carrier_capability`, `caller_id_visible`. |
| `DELETE /v1/accounts/me` | user (senior) | 3/hour | Deletes the account, phone index row, devices, invites, sessions, and the Firebase Auth user. Refused during a live call. Usage events keep an opaque account id until their TTL. |
| `GET /v1/accounts/consent-version` | none | none | The consent text version the app must present. |
| `POST /v1/guardians/invite` | user (senior) | 3/hour | Body: guardian `phone`, `name`, `relationship`. Creates an invite keyed by the guardian's phone hash. |
| `POST /v1/guardians/link` | user (guardian, own device) | 5/hour | No body. Matches the caller's verified phone to an open invite. Sets `active_at = now + 24h`. |
| `GET /v1/guardians/accounts` | user | 30/min | Accounts the caller guards. |
| `DELETE /v1/guardians/accounts/{id}` | user (guardian) | 10/hour | The guardian removes themselves. |
| `POST /v1/devices`, `DELETE /v1/devices` | user | 10/min | FCM token registration. |
| `POST /v1/sessions/intent` | user (senior) | 5/min | Returns `session_id`, `guardian_line_number`, `expires_at`. |
| `GET /v1/sessions/{id}` | user (senior or active guardian) | 60/min | `Session.public_view()`. |
| `GET /v1/sessions` | user | 30/min | Recent sessions for the caller's account. |
| `POST /v1/sessions/{id}/feedback` | user | 10/min | Body: `false_alarm: bool`, optional `note` from a fixed enum. |
| `POST /internal/sweep` | Cloud Scheduler OIDC | none | Expires stale intents and abandons sessions past `max_session_minutes`. |
| `POST /internal/rollup` | Cloud Scheduler OIDC | none | Writes `usage_monthly` for the current and previous month. |
| `GET /admin/usage` | user with `staff` claim | 30/min | Month-to-date and last-month rollups. |

Dev auth (`AUTH_MODE=dev`): `X-Dev-Uid` and `X-Dev-Phone` headers stand in for a Firebase token. Refused when `ENV=prod`.

## Identity and trust

- The senior signs in with phone OTP on the senior's phone. The verified phone number from the token is what `phone_index` keys on, so the Guardian Line only accepts calls from numbers that proved possession.
- Guardian linking starts on the senior's phone (invite) and completes on the guardian's own phone (link). The guardian's alerts and voice go live 24 hours after linking. The senior's phone and existing guardians are notified at link time.
- Staff access is a Firebase custom claim `staff: true`, set with `infra/scripts/grant_staff.py`, never from the app.

## Cloud Run service

`infra/cloudrun.yaml`, applied with `gcloud run services replace`. 1 vCPU, 2 GiB, request-based billing, min 1, max 1, concurrency 80, request timeout 3600 s, startup CPU boost, session affinity on, HTTP/1 (WebSockets). Runtime service account `elderguard-api@PROJECT.iam.gserviceaccount.com` with `roles/datastore.user`, `roles/secretmanager.secretAccessor` on each secret, `roles/firebasecloudmessaging.admin`, and `roles/storage.objectAdmin` on the one bucket. Never Editor.

## Scheduled and reactive jobs

| Job | Trigger | Target |
|---|---|---|
| `sweep` | Cloud Scheduler every minute | `POST /internal/sweep` |
| `rollup` | Cloud Scheduler daily 02:10 America/Los_Angeles | `POST /internal/rollup` |
| `budget-killswitch` | Pub/Sub from the billing budget at 100% | Sets `config/providers.limits.kill_switch = true`, repoints the Twilio number to the fallback TwiML Bin, emails the operator. Never disables billing. |

## Carrier matrix *(pending spike)*

| Carrier | Phone | Merge offered | Seconds to Merge | Far party hears | Who ends the conference | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |

## Real-call findings *(pending M0 test)*

Filled in from `docs/M0-REAL-CALL.md`: confirm-sheet name shown, seconds to Merge, transcript quality, time from "gift card" to `tier=stop`.
