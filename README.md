# ElderGuard

**A scam-call guardian for the people scammers target most.**

Elder fraud is a multi-billion-dollar problem, and the classic playbook — fake IRS agents, "grandchild in trouble" calls, gift-card demands, tech-support takeovers — works because it isolates the victim in the moment. ElderGuard puts a trusted family member's presence *into* that moment: it watches a live phone call, scores it for scam patterns with Claude, and speaks to Mom in the voice of someone she already trusts.

> **We guard elders, so we guard ourselves.** A tool that protects vulnerable people can't ship its own attack surface — every change here gets a security review before a feature review. See [Security posture](#security-posture).

---

## What it does

ElderGuard has two protective modes, both framed as a letter from a real family member (in the prototype, "Jarmar" protecting "Mom"):

**🛡 Live call guardian.** During a phone call, the transcript is streamed to an analysis service that scores it 0–10 against known scam patterns (government impersonation, payment-by-gift-card, urgency and isolation tactics, info fishing, and more). The UI escalates with the score:

| Score | State | What Mom sees |
|-------|-------|---------------|
| 0–3 | Clear | Quiet reassurance — the call looks normal |
| 4–6 | Caution | A visible warning with the specific red flags, in plain language |
| 7–10 | Takeover | "End the call now" — with guidance written in her family member's voice |

There are also honest failure states — *checking*, *no voice detected*, and *false alarm* — because a guardian that pretends to be certain is itself a hazard.

**✉️ "Show Me" message check.** Outside of calls, Mom can show ElderGuard a suspicious text, email, or voicemail and answer two short questions. She gets one of three verdicts — *looks OK*, *be careful*, or *don't respond* — written conservatively and in familiar language, never in scammer-speak.

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  Frontend                   │  HTTPS  │  Backend                     │
│  Vite + React + TypeScript  │ ──────► │  FastAPI (Python)            │
│  Cloudflare Pages           │         │  POST /analyze               │
│                             │         │  GET  /health                │
│  • 19 hi-fi screens, 4 flows│         │        │                     │
│  • Custom design system     │         │        ▼                     │
│  • State-machine navigator  │         │  Anthropic Claude            │
│                             │         │  (scam-pattern scoring,      │
└─────────────────────────────┘         │   strict JSON contract)      │
                                        └──────────────────────────────┘
```

### Backend — [`backend/`](backend/)

A small, focused FastAPI service ([`main.py`](backend/main.py)):

- **`POST /analyze`** takes `{ transcript, call_duration_seconds }` and returns a typed, bounded response:

  ```json
  {
    "score": 8,
    "reasoning": "Caller impersonates the IRS and demands gift cards under arrest threat.",
    "red_flags": ["GOVERNMENT IMPERSONATION", "UNUSUAL PAYMENT", "URGENCY"],
    "recommendation": "END CALL NOW"
  }
  ```

- The scoring rubric and known-pattern taxonomy live in a single reviewable system prompt ([`prompts.py`](backend/prompts.py)). The model must return strict JSON; the recommendation tier (`SAFE` / `CAUTION` / `END CALL NOW`) is then **re-derived server-side from the numeric score**, so a manipulated or malformed model response can't hand the UI an inflated "all clear."
- **Fails safe and conservative:** short/empty transcripts and analysis errors return a neutral result rather than crashing mid-call or fabricating a verdict.
- Pydantic models validate every request and response at the boundary.

### Frontend — [`frontend/`](frontend/)

Vite + React + TypeScript, deployed to Cloudflare Pages. All **19 hi-fi screens across 4 flows** are implemented and wired into a real navigation state machine — plus a floating "Screens" dock for jumping to any state directly (useful for demos and design review):

| Flow | Screens |
|------|---------|
| Onboarding | Splash + 4 setup steps — the *family member* configures the app on Mom's phone |
| Home / Profile | Idle home ("Hi Mom — I've got your back") and profile |
| Live call | Clear · Caution · Checking · Takeover · No-voice · False-alarm |
| Show Me | Intake, 2 clarifying questions, and 3 verdict screens (OK / Care / No) |

The UI is built on a small custom design system ([`src/design-system/`](frontend/src/design-system/)) — a **"warm letter" aesthetic**: cream paper, navy ink, brass accents, coral alerts, with primitives like `Letterhead`, `Signature`, `FromLine`, and `BrassDial`. The intent is deliberate: safety guidance lands better as a note from your son than as a red error dialog, and large type + high contrast + one-action screens are accessibility choices for elderly users, not styling ones.

> **Current integration status:** the frontend presently stubs its backend calls — the call-state transitions and Show-Me verdict resolver are the marked integration points for wiring in `/analyze`. The backend is fully functional standalone. Honest status beats a rigged demo.

## Design decisions worth noting

- **The trusted-voice framing is the product.** Scam scripts work by manufacturing authority and urgency. ElderGuard counters with the one authority scammers can't fake — a named family member — and every screen is written in that person's voice.
- **The AI is bounded, not chatty.** Claude never free-texts at the user mid-crisis. It returns a score, one sentence of reasoning, and an enumerated flag list; the app owns all user-facing language. An LLM output surfaced to a frightened 78-year-old is itself an attack surface, and it's treated like one.
- **Conservative by default.** Every ambiguous path (short transcript, API failure, unclear answers) degrades toward calm, not alarm — and never toward "this call is safe, proceed" on the model's word alone.

## Security posture

This repo is public from day one and treats that as a design constraint, not a risk:

- **No secrets in the repo, ever.** Config comes from a gitignored `.env`; [`.env.example`](.env.example) contains placeholders only. Commits are secret-scanned before they leave the machine.
- **Least privilege.** Per-environment, single-project API tokens; input validation at every HTTP boundary; security headers (`X-Frame-Options: DENY`, `nosniff`, strict referrer policy) shipped via Cloudflare Pages [`_headers`](frontend/public/_headers).
- **Threat-modeled as a product.** The core question asked of every feature: *what does an attacker who controls X get to do?* — where X includes the transcript, the prompt, and the model output. The full operating policy is in [`CLAUDE.md`](CLAUDE.md).

## Running it yourself

ElderGuard is fork-ready: everything you need is your own free-tier accounts. No private registries, no "ask the maintainer for access."

**You'll provision:** an [Anthropic API key](https://console.anthropic.com/settings/keys), and (for hosting only) a Cloudflare account.

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then put your real ANTHROPIC_API_KEY in .env
uvicorn main:app --reload
```

Smoke test:

```bash
curl -s localhost:8000/health
curl -s localhost:8000/analyze -X POST -H 'Content-Type: application/json' \
  -d '{"transcript": "This is the IRS. You owe back taxes. Buy Apple gift cards in the next hour or a warrant is issued. Do not tell your family."}'
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Deployment to Cloudflare Pages (Wrangler or Git-connected) is documented in [`frontend/README.md`](frontend/README.md).

## Roadmap

- Wire the frontend's call-state machine and Show-Me resolver to the live `/analyze` endpoint
- Real-time audio → transcript ingestion (streaming STT) for the live-call flow
- Voice responses in the trusted contact's voice (ElevenLabs)
- Verifiable trusted-contact identity (anyone who can spoof the family member can drive Mom's trust — this is the highest-value target in the threat model)
- Backend hosting on a managed runtime with built-in secret management; CORS allow-list + rate limiting before public traffic
- Encrypted-at-rest, minimum-retention handling for any stored audio (voice is biometric data)

## Project layout

```
backend/            FastAPI scam-analysis service (Claude-powered)
  main.py           API: /health, /analyze
  prompts.py        Scoring rubric + scam-pattern taxonomy (single reviewable prompt)
frontend/           Vite + React + TS — 19 screens, 4 flows
  src/design-system/  Warm-letter primitives (Phone, Letterhead, BrassDial, …)
  src/screens/        onboarding · home · call · show
  src/navigator/      State-machine navigation + screen-jump dock
.env.example        Placeholder env template (never real values)
CLAUDE.md           Binding security-first operating policy for this repo
```

---

Built by [Jarmar Ledesma](https://github.com/todezwood).
