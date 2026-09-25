# ElderGuard — Claude operating instructions

> **We guard elders, so we guard ourselves.**
> ElderGuard's purpose is to protect vulnerable people from attackers. A project with that mission cannot ship its own attack surface. Every decision — code, infrastructure, dependencies, deploy, docs — gets a security review *before* a feature review.

This file is loaded automatically into every Claude session on this project. Treat it as binding operating policy, not background context.

## Repo intent

- **Open-source from day one.** This repo is and will remain public. Assume any commit is immediately world-readable. Never rely on "private for now" as a security boundary.
- **Fork-ready.** Someone should be able to clone, provision their own credentials, and run their own ElderGuard. No hidden operational state, no proprietary dependencies, no licensed assets, no embedded keys.
- **Defensive product.** This is a tool that vulnerable users (e.g., elderly relatives) and their guardians depend on during high-stakes moments. Bugs and leaks here have human cost, not just reputational cost.

## Security-first directives

These are non-negotiable defaults. Don't relax any of them without an explicit, in-conversation discussion with Jarmar about the tradeoff.

### 1. Secrets never enter the conversation

- **If Jarmar (or anyone) pastes an API key, token, password, private cert, session ID, OAuth secret, or webhook signing key into chat: treat it as already compromised the moment it lands in the transcript.** Tell them to revoke it immediately. Do not echo it, store it in a file, use it for a request, or "remember it for later." Ask them to put it in a gitignored `.env` and reference it from there.
- Never write a secret value into source, config, comments, fixtures, test data, or example files. `.env.example` contains placeholder strings only (e.g. `ANTHROPIC_API_KEY=your-anthropic-api-key-here`), never real values.
- Same rule applies to *received* secrets — if a tool result echoes a key from logs or config, do not propagate it. Flag it.

### 2. Every commit and push is secret-scanned before it leaves the machine

Before `git add` / `git commit` / `git push`, grep staged content for:
- `sk-`, `sk-ant-`, `xoxb-`, `xoxp-` — API key prefixes (Anthropic, Slack, etc.)
- `ghp_`, `gho_`, `ghs_`, `github_pat_` — GitHub tokens
- `AKIA`, `ASIA` — AWS access keys
- `AIza` — Google API keys
- `Bearer ` followed by a long string
- JWT shape: `eyJ` followed by base64-ish content
- Any line matching `(KEY|TOKEN|SECRET|PASSWORD|PRIVATE)\s*[:=]\s*\S{20,}` outside of clearly-labeled placeholders

Stage **specific files by path**, never `git add .` or `git add -A`. Show Jarmar the file list before push and wait for explicit approval. Never `git push` without confirmation, even if previously approved for a different push.

### 3. Infrastructure gets least-privilege by default

- GCP service accounts and CI identities scoped to a single project with only the roles they use; never Owner or Editor. Same rule for any third-party token (Twilio, Cloudflare for the website repo).
- API tokens (Anthropic, ElevenLabs, future providers) created per-environment (dev/prod), revocable, never shared between repos.
- CORS allow-lists, not `*`. Auth required on any endpoint that returns user data or triggers side effects.
- Rate limiting on any public endpoint, especially anything that triggers paid AI calls.
- Input validation at every boundary (HTTP body, query params, file uploads, transcript ingestion).
- Storage buckets / databases default to private; public access is explicit and reasoned.
- Never disable security features (`--no-verify`, `verify=false`, `--insecure`, `*` CORS, disabled CSP) without Jarmar explicitly asking and a discussion of the threat model.
- Flag dependency vulnerabilities when they surface (e.g., `npm audit`). Don't silently ignore.

### 4. Threat model the product, not just the code

ElderGuard sits between an attacker (scammer) and a vulnerable user. The AI's *output* is itself an attack surface:
- A scammer who can manipulate transcripts, prompts, or scoring can turn ElderGuard into a tool that *reassures* the victim during a real scam ("ElderGuard says reply"). LLM outputs surfaced to Mom must be bounded, conservative-by-default, and clearly distinguishable from caller speech.
- Trusted-contact identity (Jarmar) must be verifiable. Anyone who can spoof Jarmar can drive Mom's trust.
- Stored audio is biometric data. Encrypt at rest, minimize retention, document the deletion path for forks.
- Logs collect enough to debug failures, not enough to reconstruct private conversations or leak PII.

When proposing features, name the failure mode. "What does an attacker who controls X get to do?" is the framing.

### 5. Open-source readiness is a security property

- A `LICENSE` file at root (Jarmar picks: MIT or Apache-2) before public traffic.
- README explains exactly what a fresh forker has to provision: their own GCP and Firebase project, Twilio account, Anthropic key, transcription key, and later ElevenLabs key. No "ask Jarmar for access" steps.
- No private registries, no proprietary fonts/assets requiring licenses, no copy-pasted code without attribution.
- Issue templates and contribution docs eventually — but only when there's something for contributors to do.

## Pre-push checklist (run every time)

1. `git status` — confirm only intended files are staged.
2. Secret scan over staged content (patterns above).
3. Confirm `.env`, `.env.local`, `.dev.vars`, any `*.key` / `*.pem` / `credentials.json` are not staged.
4. Show Jarmar the file list and the destination remote/branch.
5. Wait for explicit "push" or equivalent. Don't infer consent from earlier approvals.

## Project layout

- [backend/](backend/) — Python FastAPI service: Guardian Line voice webhooks, Twilio media-stream WebSocket, rolling scam scoring, pluggable AI providers. Reads secrets from `.env` locally and Secret Manager in prod.
- [mobile/](mobile/) — Expo / React Native app for iOS and Android (from M2).
- [prototype/](prototype/) — the original Vite/React click-through, frozen as a visual reference. Not deployed, not maintained. Deleted once every screen exists in `mobile/`.
- [infra/](infra/) — GCP bootstrap script, Cloud Run service spec, Firestore rules, Twilio setup (from M1).
- [docs/](docs/) — architecture, threat model, data retention, legal notes, fork guide, runbook, and the policy text the website hosts.
- **Website:** elderguard.org is built and hosted on Cloudflare from a separate repo (`todezwood/eldergaurd-website`). Nothing in this repo deploys it; this repo only drafts the privacy, terms, and data-deletion copy it needs.
- [.env.example](.env.example) — placeholder env template. **Never** contains real values.

## Hosting / infra choices on this project

- **Platform:** GCP, lean. Cloud Run (request-based billing, min 1 / max 1 at launch), Secret Manager, Firebase Auth (phone), Firestore, Firebase Cloud Messaging, one private GCS bucket. No Terraform at this scale; `infra/bootstrap.sh` is the source of truth for provisioning.
- **Telephony:** Twilio Guardian Line with Media Streams. Fallback TwiML plays a notice when the backend is down. Auto-recharge off so the prepaid balance is a hard cost cap.
- **AI providers:** pluggable behind `backend/app/providers/`. Anthropic scores, Deepgram transcribes at launch, with fallbacks configured in `backend/config/providers.default.yaml`. `FAKE_PROVIDERS=1` runs everything with no credentials.
- **Mobile:** Expo / React Native, one codebase, EAS builds.
- **Cost posture:** self-funded until grants. Budget alert with a kill switch, Anthropic spend limit, STT quota, and per-account minute caps are part of the deploy, not optional extras.

## Product constraints that are not derivable from code

- iOS and Android do not let a store app hear a native cellular call. The live guardian works by the senior merging the call with the Guardian Line. Do not propose on-device listening.
- There is no "safe" tier while a call is live. Tiers are Listening, Caution, Stop, plus Unknown and No-audio. Any fallback that would tell the senior a call is safe is a bug.
- Guardians link from their own device only, with a cool-off, and guidance text comes from fixed templates. Free-text guidance from a guardian is a spoofing surface.
- Live listening by a third party is interception in all-party-consent states. The monitoring announcement defaults on and a consent screen is required. Counsel reviews before any non-Jarmar user.
