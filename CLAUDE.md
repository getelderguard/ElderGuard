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

- Cloudflare/Wrangler tokens scoped to a single project, never account-wide unless required.
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
- README explains exactly what a fresh forker has to provision: their own Anthropic key, their own Cloudflare account, their own ElevenLabs key, etc. No "ask Jarmar for access" steps.
- No private registries, no proprietary fonts/assets requiring licenses, no copy-pasted code without attribution.
- Issue templates and contribution docs eventually — but only when there's something for contributors to do.

## Pre-push checklist (run every time)

1. `git status` — confirm only intended files are staged.
2. Secret scan over staged content (patterns above).
3. Confirm `.env`, `.env.local`, `.dev.vars`, any `*.key` / `*.pem` / `credentials.json` are not staged.
4. Show Jarmar the file list and the destination remote/branch.
5. Wait for explicit "push" or equivalent. Don't infer consent from earlier approvals.

## Project layout

- [backend/](backend/) — Python service (Anthropic-powered scam analysis). Reads secrets from `.env`.
- [frontend/](frontend/) — Vite + React + TS. Hosted on Cloudflare Pages (see [frontend/README.md](frontend/README.md)).
- [.env.example](.env.example) — placeholder env template. **Never** contains real values.

## Hosting / infra choices on this project

- **Frontend:** Cloudflare Pages (Jarmar is exploring Cloudflare; already familiar with Vercel).
- **Backend:** Python (currently `backend/main.py`). Hosting target TBD — when chosen, default to managed runtime with secret-management built in.
