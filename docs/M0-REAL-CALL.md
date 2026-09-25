# M0 runbook: hear a real merged call and score it

This is the manual test that proves the platform bet. It takes three phones and about an hour the first time. Do the one-day carrier spike from the plan first if you have not; this runbook assumes Merge Calls works on the senior phone's carrier.

## You need

- A Twilio account with one local voice number (trial accounts can only call verified numbers, so upgrade or verify every phone you use).
- An Anthropic API key and a Deepgram API key, both created for dev only and revocable.
- `ngrok` installed and logged in (`brew install ngrok`, then `ngrok config add-authtoken ...`).
- Three phones: the "senior" phone (enrolled), a "caller" phone (plays the scammer), and any third line is optional.

## One-time setup

1. Copy the env template and fill it in. Never paste keys into chat or commit `.env`.

   ```bash
   cp .env.example .env
   python3 -c 'import secrets; print(secrets.token_hex(32))'   # run twice, paste into PHONE_HASH_PEPPER and STREAM_TOKEN_SECRET
   ```

   Set `DEV_ALLOWED_PHONES` to the senior phone's number in E.164, for example `+14155550142`. Set `TWILIO_GUARDIAN_NUMBER` to your Twilio number.

2. Save the Twilio number in the senior phone's contacts as **ElderGuard**, and add it to Favorites. This is what the iOS confirm sheet and the in-call screen will show.

3. Start the backend and the tunnel in two terminals:

   ```bash
   cd backend && uv sync && uv run uvicorn app.main:create_app --factory --port 8000
   ngrok http 8000
   ```

   Put the `https://...ngrok.app` origin into `PUBLIC_BASE_URL` in `.env` and restart the backend. Signature validation uses this exact origin, so it must match what Twilio sees.

4. In the Twilio console, on the number: Voice configuration, "A call comes in" = Webhook, `https://<ngrok>/twilio/voice/inbound`, HTTP POST. Set the **primary handler fails** fallback to a TwiML Bin that says the fallback notice (see `app/telephony/twiml.py`, `FALLBACK_NOTICE`). Set the call status callback to `https://<ngrok>/twilio/voice/status`.

5. Sanity check without a phone:

   ```bash
   curl -s localhost:8000/ready
   ```

   You should see `scorer_routes: ["anthropic"]` and `transcriber_routes: ["deepgram"]`. If either list is empty, the key for that provider is missing.

## The test

1. From the caller phone, call the senior phone. Read a gift-card scam script slowly. A good one: "This is the Medicare benefits office. Your new card is on hold. To release it I need to verify your Social Security number. There is a small processing fee. Go to the store, buy a gift card, and read me the numbers. Please don't tell anyone until this is resolved, it's a private matter."

2. On the senior phone, while the call is up, open Contacts, tap ElderGuard, tap call. Note what the confirm sheet says and how long it takes before the native **Merge Calls** button becomes active. Tap Merge.

3. Watch the backend terminal. You should see, in order:
   - `inbound_accepted` with `initiated_by=line`
   - `media_started`
   - `score` lines every few seconds with `tier`, `dial`, `score`, and `flags`
   - the dial passing 35 (Caution) and, once two consecutive high scores carry an action flag, `tier=stop`

4. Hang up from the caller phone first, then from the senior phone. You should see `call_ended`.

5. Now test the failure paths:
   - Call the Guardian Line from a phone that is not in `DEV_ALLOWED_PHONES`. It should be rejected silently and log `inbound_rejected reason=unknown_number`.
   - During a live merged call, kill the backend and restart it within a few seconds. Twilio should hit `/twilio/voice/reconnect`, you should see `reconnect_issued`, and scoring should resume.
   - Kill the backend and leave it down. Twilio's fallback TwiML Bin should play the notice.

## What to record in docs/ARCHITECTURE.md

- Carrier and phone model of the senior phone.
- Whether the confirm sheet showed the contact name.
- Seconds from tapping the contact to Merge Calls becoming active.
- Whether the far party heard hold music or a beep.
- Which side's hangup ended the conference.
- Transcript quality: could you read the scam lines back from the logs at DEBUG level?
- Time from saying "gift card" to `tier=stop` in the logs.

## When you are done

Revoke the dev Twilio auth token, Anthropic key, and Deepgram key if any of them were ever visible on a shared screen. Rotate them again before the M1 deploy regardless.
