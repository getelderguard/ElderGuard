# ElderGuard

**A scam-call guardian for the people scammers target most.**

Elder fraud is a multi-billion-dollar problem, and the classic playbook works because it isolates the victim in the moment: fake Medicare agents, "your grandson is in jail," gift-card demands, remote-access "tech support." ElderGuard puts a trusted family member's presence into that moment. During a call, the senior taps one button, and a guardian line listens alongside them, scores the call for scam patterns with an LLM, and speaks up in the family member's own recorded voice when it is time to hang up.

ElderGuard is free for seniors and their families. It is built in the open so that any organization can run its own instance, and so that AI and telephony providers can sponsor it directly.

> **We guard elders, so we guard ourselves.** A tool that protects vulnerable people cannot ship its own attack surface. Every change here gets a security review before a feature review. See [CLAUDE.md](CLAUDE.md) for the binding policy.

## How it works

Neither iOS nor Android lets a store app hear a regular phone call, so ElderGuard does not try. Instead it owns a phone number, the **Guardian Line**.

1. A call comes in. The senior taps **Check this call** in the app, or taps the ElderGuard contact from the native call screen.
2. Their phone dials the Guardian Line and they tap the native **Merge Calls** button. Carrier three-way calling now carries both voices to our line.
3. The backend streams the audio to a transcription provider, scores the rolling transcript every few seconds, and publishes a tier: **Listening**, **Caution**, or **Stop**. There is deliberately no "safe" tier while a call is live.
4. On Stop, the app vibrates and shows guidance in the guardian's words, and the line can play the guardian's recorded voice into the call.
5. A short notice that the call is protected plays once the merge completes. Scammers tend to hang up on monitored calls. Real callers do not mind.

Outside of calls, **Show Me** lets the senior photograph, paste, or describe a suspicious message and get a plain-language verdict.

## Status

| Piece | State |
|---|---|
| Backend: Guardian Line webhooks, media stream, rolling scorer, provider layer, fakes, tests | Built (M0). Not yet exercised on a real carrier call. See [docs/M0-REAL-CALL.md](docs/M0-REAL-CALL.md). |
| GCP deploy, Firebase auth, Firestore, alerts, cost guardrails | M1, next |
| Expo mobile app (iOS and Android) | M2 |
| Spoken takeover in the guardian's voice | M3 |
| Show Me with real inputs | M4 |
| Store submission, elderguard.org, fork guide | M5 |

The original 19-screen web click-through lives in [prototype/](prototype/) as a visual reference until the mobile app covers every screen.

## Architecture

```
 senior's phone ──(merge)──► Twilio Guardian Line ──► Cloud Run: FastAPI
                                                          │  Media Streams WebSocket
                                                          │  streaming STT (Deepgram, pluggable)
                                                          │  rolling LLM scoring (Claude, pluggable)
                                                          ▼
 Expo app ◄──── Firestore session doc (tier, dial) ◄───── session store
           ◄──── FCM push on tier change
```

- **Backend** ([backend/](backend/)): Python, FastAPI. `POST /twilio/voice/inbound` answers the line, rejects unknown or anonymous callers silently, and returns TwiML that streams audio to `WS /twilio/media`. A `<Redirect>` after the stream reconnects automatically if the backend blips. The scorer uses an evidence gate, adaptive cadence, a regex trip-wire, and hysteresis so a single hallucinated score cannot tell someone to hang up on their doctor. Provider failures produce `unknown`, never a safe-looking result.
- **Providers** ([backend/app/providers/](backend/app/providers/)): four protocols (scorer, streaming transcriber, voice synthesizer, message analyzer), a config-driven registry, per-call usage and cost events. `FAKE_PROVIDERS=1` runs the whole system with no credentials.
- **Mobile**: Expo / React Native, one codebase for both stores. The warm-letter design system (cream paper, navy ink, brass dial) carries over from the prototype.
- **Infra**: GCP, kept small. Cloud Run at one instance, Firestore, Firebase Auth by phone number, Cloud Messaging, Secret Manager. Budget alert wired to a kill switch. Provisioned by a documented bootstrap script rather than Terraform.

## Running it yourself

Everything a forker needs is their own free-tier or pay-as-you-go accounts. No private registries, no "ask the maintainer."

**You provision:** a GCP project with billing, a Firebase project with phone sign-in, a Twilio account and one local number, an Anthropic API key, a Deepgram API key (or another supported transcriber), and, for hosting only, a domain. Apple Developer and Google Play accounts for store builds.

### Backend, locally, with no credentials

```bash
cd backend
uv sync
FAKE_PROVIDERS=1 uv run uvicorn app.main:create_app --factory --reload
curl -s localhost:8000/ready
uv run pytest
```

### Backend against real providers and a real phone

Follow [docs/M0-REAL-CALL.md](docs/M0-REAL-CALL.md). Secrets go in a gitignored `.env` copied from [.env.example](.env.example).

## Security posture

- No secrets in the repo. Placeholders only in `.env.example`. Commits are secret-scanned before they leave the machine.
- Every Twilio webhook validates the request signature against the configured public URL. The media socket requires a short-lived token bound to the session and call.
- Phone numbers are stored only as a peppered hash. No transcripts or call audio are stored. Logs redact transcript and phone fields.
- The LLM returns a bounded score and enumerated flags; the server derives the tier after clamping. Anything in a call that addresses ElderGuard or claims the call is safe is itself a red flag.
- Guardians link only from their own device with a cool-off, and guidance uses fixed templates, so a scammer on the line cannot make himself the trusted voice.
- Live listening is interception under all-party-consent laws in some states. The monitoring notice is on by default and a consent screen is required. Counsel reviews before any user beyond the maintainer.

The full threat model and data-retention policy land in `docs/` during M1.

## Roadmap

Automatic merge on Android via the default-phone-app role; number forwarding for landlines and flip phones; a Bluetooth companion for homes that want no phone-plan changes; weighted routing across sponsoring AI providers with a usage dashboard for grant reporting.

## License

To be chosen before the first deploy: Apache-2.0 is recommended.

---

Built by [Jarmar Ledesma](https://github.com/todezwood).
