#!/usr/bin/env python3
"""Point the Guardian Line number at the backend and install the cost guardrails.

  twilio_setup.py --base-url https://api.elderguard.org [--dry-run]
  twilio_setup.py --base-url https://abc.ngrok.app --daily-minutes 60 --monthly-spend 50

Reads TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_GUARDIAN_NUMBER from the environment
(or a .env in the repo root). Never prints the token. What it does:

  1. Creates or updates a TwiML Bin named "elderguard-fallback" whose body is the FALLBACK_NOTICE
     from backend/app/telephony/twiml.py, then a <Hangup/>.
  2. Sets the number's voice URL (POST /twilio/voice/inbound), voice fallback URL (the Bin),
     and status callback (POST /twilio/voice/status).
  3. Creates usage triggers: daily inbound minutes over --daily-minutes, and monthly total
     spend over --monthly-spend, both posting to /twilio/voice/status-trigger.

Auto-recharge OFF and the low-balance email notification are console-only; the API cannot
set either. With auto-recharge off the prepaid balance is the hard cap.
"""

from __future__ import annotations

import argparse
import os
import sys
from xml.sax.saxutils import escape

from _common import REPO_ROOT, add_backend_to_path

add_backend_to_path()

from app.telephony.twiml import FALLBACK_NOTICE  # noqa: E402

BIN_NAME = "elderguard-fallback"


def _load_dotenv() -> None:
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def fallback_twiml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Say>{escape(FALLBACK_NOTICE)}</Say><Hangup/></Response>"
    )


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--base-url", required=True, help="PUBLIC_BASE_URL the backend is configured with"
    )
    p.add_argument("--daily-minutes", type=int, default=120)
    p.add_argument("--monthly-spend", type=float, default=100.0, help="USD")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    _load_dotenv()
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    number = os.environ.get("TWILIO_GUARDIAN_NUMBER")
    if not (sid and token and number):
        sys.exit("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_GUARDIAN_NUMBER must be set")

    base = args.base_url.rstrip("/")
    voice_url = f"{base}/twilio/voice/inbound"
    status_url = f"{base}/twilio/voice/status"
    trigger_url = f"{base}/twilio/voice/status-trigger"

    print(f"account:  {sid[:6]}... (token not shown)")
    print(f"number:   {number}")
    print(f"voice:    POST {voice_url}")
    print(f"status:   POST {status_url}")
    print(f"fallback: TwiML Bin '{BIN_NAME}':")
    print("          " + fallback_twiml())
    if args.dry_run:
        print("dry-run: nothing changed")
        return 0

    from twilio.rest import Client

    client = Client(sid, token)

    # 1. TwiML Bin. The Bins API lives under the serverless/"TwiML Bins" product; the REST path
    # is https://twiml-bins.twilio.com. The python SDK exposes it through client.request.
    bins = client.request(
        "GET", "https://twiml-bins.twilio.com/v1/TwimlBins", params={"PageSize": 100}
    )
    existing = next(
        (b for b in bins.json().get("twiml_bins", []) if b.get("friendly_name") == BIN_NAME), None
    )
    payload = {"FriendlyName": BIN_NAME, "Twiml": fallback_twiml()}
    if existing:
        resp = client.request(
            "POST", f"https://twiml-bins.twilio.com/v1/TwimlBins/{existing['sid']}", data=payload
        )
    else:
        resp = client.request("POST", "https://twiml-bins.twilio.com/v1/TwimlBins", data=payload)
    bin_url = resp.json()["url"]
    print(f"fallback bin url: {bin_url}")

    # 2. Number configuration.
    numbers = client.incoming_phone_numbers.list(phone_number=number, limit=1)
    if not numbers:
        sys.exit(f"{number} is not on this account")
    numbers[0].update(
        voice_url=voice_url,
        voice_method="POST",
        voice_fallback_url=bin_url,
        voice_fallback_method="GET",
        status_callback=status_url,
        status_callback_method="POST",
    )
    print("number updated")

    # 3. Usage triggers (idempotent by friendly name).
    wanted = {
        "elderguard-daily-minutes": dict(
            usage_category="calls-inbound",
            trigger_value=str(args.daily_minutes),
            trigger_by="usage",
            recurring="daily",
        ),
        "elderguard-monthly-spend": dict(
            usage_category="totalprice",
            trigger_value=str(args.monthly_spend),
            trigger_by="price",
            recurring="monthly",
        ),
    }
    current = {t.friendly_name: t for t in client.usage.triggers.list(limit=100)}
    for name, spec in wanted.items():
        if name in current:
            current[name].update(
                callback_url=trigger_url, callback_method="POST", friendly_name=name
            )
            print(f"trigger {name}: updated")
        else:
            kwargs = {k: v for k, v in spec.items() if v != ""}
            client.usage.triggers.create(
                callback_url=trigger_url,
                callback_method="POST",
                friendly_name=name,
                **kwargs,
            )
            print(f"trigger {name}: created")

    print(
        "\nRemember: auto-recharge OFF and a low-balance notification, both in the Twilio console."
    )
    print("Then set FALLBACK_TWIML_URL on the")
    print(f"budget-killswitch function to {bin_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
