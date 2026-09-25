# Data retention and deletion

What ElderGuard touches, where it lives, how long it stays, and how it is deleted. The site's privacy policy and the store privacy labels are derived from this table and must not promise anything it does not say. When the code changes what is stored, this file changes in the same commit.

Status legend: **M0** is what the code does today, **M1** and later are planned and not yet enforced by code.

## Principles

1. No call audio is ever written to disk or to a bucket. It passes through memory to the transcription provider and is gone.
2. No transcript is ever stored. Scoring uses a rolling 90-second window in memory. `Session.transcript_stored` is always `false`.
3. Phone numbers are stored only as a peppered HMAC-SHA256 hash plus the last four digits. The pepper is a separate secret.
4. Everything with a retention period has a Firestore TTL field or a Cloud Logging retention setting, not a cron job someone has to remember.
5. Deleting an account removes everything that can identify the person, end to end, including the Firebase Auth user.

## Data inventory

| Element | Where it lives | Form | Retention | Deletion path | Who can read it | Status |
|---|---|---|---|---|---|---|
| Call audio (both parties, after merge) | Backend process memory; Twilio Media Streams in transit; Deepgram for transcription | Raw mulaw 8 kHz, never persisted | Duration of the call. Buffered frames are discarded on stream close. | Nothing to delete. Deepgram: operator enables zero data retention on the project (verify availability on the plan). | No one after the call. | M0 |
| Transcript segments | Backend process memory (`RollingTranscript`, last 90 s or 1,500 chars) | Plain text | Duration of the call | Nothing to delete | No one. Redacted from logs above DEBUG. | M0 |
| Transcript window sent for scoring | Anthropic Messages API request | Plain text, up to 1,500 chars plus 200 chars of partial | Anthropic's API retention. Operator uses an organisation with zero data retention where available and never enables training on this data. | Anthropic data controls | Anthropic per its terms | M0 |
| Score, flags, reasoning | `sessions/{id}` in Firestore; structured logs | Integer, enum list, up to 240 chars of model text | Session document: 30 days (TTL on `expire_at`). Logs: 30 days. | Account deletion removes the session documents immediately. | Senior and active guardians see tier, dial, score, flags. Reasoning is server and guardian only. | M1 (TTL); M0 (in memory) |
| Phone number, senior | `phone_index/{phone_hash}` and `accounts/{id}.senior.phone_last4`; Firebase Auth user record | HMAC-SHA256 with pepper; last four digits in the clear; full number inside Firebase Auth | Life of the account | Account deletion removes the index row, the account document, and the Firebase Auth user. | Backend service account. No client reads the index. Firebase Auth: project owner. | M1 |
| Phone number, guardian | `phone_index`, `accounts/{id}.guardians[].phone_last4`, `guardian_invites` | Same as senior | Invite: 7 days. Linked guardian: until unlinked or the account is deleted. | Unlink removes the index row and the guardian entry. | Same as above | M1 |
| Phone number in transit | Twilio webhook form (`From`) | Plain E.164 | Handled per request; hashed immediately; redacted from logs. Twilio keeps its own call log (see below). | Twilio console | Backend, Twilio | M0 |
| Names | `accounts/{id}`: `senior.display_name`, `senior.nickname`, `guardians[].name`, `guardians[].relationship` | Plain text | Life of the account | Account deletion | Senior, that account's guardians, backend | M1 |
| Watch list | `accounts/{id}.watch_list` | Plain text, short phrases | Life of the account | Account deletion or PATCH | Same as names. Also sent to the scorer as context. | M1 |
| Consent record | `accounts/{id}.senior.consent_version`, `consent_at` | Version string and timestamp | Life of the account, then kept in the deletion record for 1 year (see below) | Account deletion (except the anonymised deletion record) | Backend, senior | M1 |
| Carrier capability, caller ID visibility | `accounts/{id}.senior.carrier_capability`, `caller_id_visible` | Booleans and small enums | Life of the account | Account deletion | Backend, senior | M2 |
| Session records | `sessions/{id}` | See `docs/ARCHITECTURE.md`. Includes `call_sid`, timestamps, tier history summary, funnel timestamps, provider choices, feedback. No text. | 30 days (TTL) | Account deletion removes all sessions for the account immediately. | Senior, active guardians, backend | M0 (memory), M1 (Firestore) |
| Usage events | `usage_events/{auto}` | Provider, model, token and audio counts, estimated cost, `session_id`, `account_id` | 90 days (TTL) | On account deletion, `account_id` is cleared to `deleted` so aggregate cost reporting survives without a link to a person. | Backend, `/admin/usage` (staff) | M1 |
| Monthly usage rollups | `usage_monthly/{YYYY-MM}` | Aggregates only, no account ids | Indefinite (this is the grant report) | Not personal data | Staff | M1 |
| Guardian voice template clips | Private GCS bucket, path recorded in `accounts/{id}.voice` | Audio files (transcoded to mulaw 8 kHz at upload), a few seconds each, fixed template lines | Until the guardian deletes them or the account is deleted | `DELETE /v1/accounts/me/voice` (M3) and account deletion. Bucket has no public access and no versioning. | Backend only. Played into the senior's call on STOP. | M3 |
| Device push token | `devices/{uid}` | FCM registration token, platform, app version | Until the app re-registers or the account is deleted | `DELETE /v1/devices`, account deletion | Owner, backend | M1 |
| Firebase Auth user | Firebase Authentication | uid, phone number, sign-in timestamps, custom claims (`staff`) | Life of the account | Account deletion calls the Admin SDK to delete the user | Project owner via console, backend via Admin SDK | M1 |
| Application logs | Cloud Logging | Structured JSON. Transcript, window text, partial text, `text`, `from_number`, `phone`, and `From` are replaced with `[redacted]` at INFO and above. Session ids, account ids, tiers, scores, flags, provider names, latencies, and errors are logged. Nothing is logged per media frame. | 30 days | Bucket retention. Not deleted per account. | Project owner, anyone with `logging.viewer` | M0 (redaction), M1 (retention and exclusion filters) |
| Sentry events | Sentry (free tier) | Stack traces, request path, environment. Sentry data scrubbing enabled; no request bodies; `send_default_pii` off. | 30 days (Sentry default) | Sentry console | Operator | M1 |
| Firestore backups | Weekly export to a private GCS bucket; point-in-time recovery for 7 days | Full database snapshot including account and session documents | Exports kept 35 days | Bucket lifecycle rule. A deleted account may exist in a backup for up to 35 days and is never restored selectively. | Project owner | M1 |
| Twilio call records | Twilio console and API | Call SID, from and to numbers, duration, status, price. No recording (recording is never requested in TwiML). | Twilio's default retention (verify current period, historically 13 months for call logs) | Twilio API supports deleting call resources; the operator runs a monthly cleanup for calls older than 90 days (M5 runbook). | Twilio account holders | M0 (no recording), M5 (cleanup) |
| Twilio Voice Insights | Twilio | Call quality metrics | Twilio default | Operator disables Voice Insights Advanced Features and any call summary that stores media. | Twilio account holders | M1 (console setting) |
| Deepgram | Deepgram | Audio in transit; usage logs | Operator enables zero retention where the plan allows it and disables any "store audio" option. | Deepgram console | Deepgram | M1 (console setting) |
| Show Me inputs (M4) | Processed in memory; `show_checks/{auto}` stores metadata only (timestamp, input type, verdict tier) | Image, text, or audio in transit; not persisted | 90 days for metadata | Account deletion | Backend, Anthropic in transit | M4 |
| Deletion record | `deletions/{auto}` | Timestamp, SHA-256 of the account id, consent version, reason. No phone, no name, no uid. | 1 year (TTL) | Not deletable (it is the evidence that deletion happened) | Backend, staff | M1 |

## What "delete my account" does

The in-app action is `DELETE /v1/accounts/me`, implemented in `backend/app/api/accounts.py` and `AccountService.delete_account`. Without the app, the person emails the contact address from `docs/site-copy/data-deletion.md`; the staff-run path for emailed requests (`infra/scripts/delete_account.py`, with an OTP to the number on file before acting) is planned for M5. The in-app path does, in this order:

1. Verify the caller is the senior of the account (the Firebase uid equals the account id). Refuse with 409 while a call is live.
2. Delete every `sessions` document where `account_id` matches.
3. Delete the `accounts/{id}` document, the senior's `phone_index` row, the senior's `devices/{uid}` document, and every `guardian_invites` document for the account, in one batch.
4. Delete the senior's Firebase Auth user.
5. Write a `deletions` record: timestamp, SHA-256 of the account id, consent version, reason. It carries no phone number, name, or uid.

What is deliberately left:

- `usage_events` keep their `account_id` until the 90-day TTL. That id is a random Firebase uid with no phone or name attached, and the month's grant report must still add up. The account it pointed to no longer exists.
- Guardians are not deleted. They have no `phone_index` row (linking matches the invite to the phone the guardian verified on their own device, then only the uid is kept), and their Firebase user and device token may serve another senior. A guardian removes themselves with `DELETE /v1/guardians/accounts/{id}`.
- Guardian voice clips (M3) are deleted when that feature exists; the deletion path will be added to this list in the same commit.
- Logs and backups are not touched. Logs contain no name or phone number. Backups age out within 35 days.

## Store privacy labels

Derived from the inventory above. Update both stores when the inventory changes.

### Apple App Privacy

| Data type | Collected | Linked to identity | Used for tracking | Purpose |
|---|---|---|---|---|
| Contact info: phone number | Yes | Yes (it is the login) | No | App functionality, account management |
| Contact info: name | Yes (display name, nickname, guardian names) | Yes | No | App functionality |
| Contacts | No. The app writes one contact card (ElderGuard) with the user's permission; it does not read the address book. | | | |
| User content: audio data | Not collected. Call audio is processed in real time and never stored. Declare under "Audio data" only if Apple's reviewer requires disclosure of in-transit processing; if so, "not linked" and "app functionality." | | | |
| User content: photos or videos (M4 Show Me) | Not stored. Processed and discarded. Same note as audio. | | | |
| Identifiers: user ID | Yes (Firebase uid) | Yes | No | App functionality |
| Identifiers: device ID | No | | | |
| Usage data: product interaction | Yes (session tier history, funnel timestamps) | Yes | No | App functionality, analytics (aggregate cost reporting) |
| Diagnostics: crash data | Yes (Sentry) | No | No | App functionality |
| Health and fitness | No | | | |
| Financial info | No | | | |
| Location | No | | | |

Tracking: none. No third-party advertising SDKs. No data is shared with data brokers.

### Google Play Data Safety

| Category | Collected | Shared | Ephemeral | Required | Purpose |
|---|---|---|---|---|---|
| Personal info: name | Yes | No | No | Yes | App functionality |
| Personal info: phone number | Yes | No | No | Yes | App functionality, account management |
| Audio: voice or sound recordings | Processed in transit only. Declare as collected and ephemeral if Play's reviewer requires it; shared with service providers (transcription, scoring) under contract. | Yes (service providers) | Yes | Yes | App functionality |
| Photos (M4) | Processed in transit only, ephemeral | Yes (service providers) | Yes | No | App functionality |
| App activity: in-app actions | Yes | No | No | Yes | App functionality, analytics |
| App info and performance: crash logs | Yes | Yes (Sentry) | No | No | Analytics |
| Device or other IDs | Push token only | No | No | Yes | App functionality |

Security practices: data encrypted in transit (TLS everywhere, including the Twilio media stream over wss); users can request deletion in-app and by email; data is not sold. Account-deletion URL: the data-deletion page on elderguard.org.

## What a fork must configure

A fork that changes nothing in the code still has to set these outside the repo, or the promises above are false:

- [ ] Firestore TTL policies on `sessions.expire_at` and `usage_events.expire_at` (`infra/bootstrap.sh` does this).
- [ ] Cloud Logging bucket retention 30 days and the exclusion filters (`infra/bootstrap.sh`).
- [ ] `LOG_LEVEL=INFO` in production. Never DEBUG.
- [ ] Anthropic organisation: zero data retention where available, training opt-out, spend limit.
- [ ] Deepgram project: zero retention or storage off.
- [ ] Twilio: no `<Record>` anywhere, Voice Insights advanced features off, auto-recharge off, monthly call-log cleanup.
- [ ] Sentry: `send_default_pii` off, data scrubbing on.
- [ ] Firestore weekly export bucket with a 35-day lifecycle rule and no public access.
- [ ] Voice clip bucket private, no versioning, uniform bucket-level access.
- [ ] The site's privacy policy and data-deletion page published at URLs the store listings point to, with the same retention periods as this file.
