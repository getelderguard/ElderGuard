"""Budget kill switch. Pub/Sub-triggered Cloud Run function.

The billing budget publishes a JSON notification on every threshold. When cost has reached the
budget amount this function:

  1. sets config/providers.limits.kill_switch = true (the API rejects new Guardian Line calls
     within CONFIG_CACHE_SECONDS), and appends a config_history row;
  2. if TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_GUARDIAN_NUMBER and FALLBACK_TWIML_URL are
     set, repoints the number's voice URL at the fallback TwiML Bin so callers hear the notice
     even if the API is later scaled to zero.

It never disables billing: that would take Firestore and Auth down with it. Idempotent: a
second notification for the same budget period is a no-op. Turning the switch back off is a
human decision: infra/scripts/set_provider.py --kill-switch off, then twilio_setup.py.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import logging
import os

import functions_framework
from google.cloud import firestore

log = logging.getLogger("budget-killswitch")
logging.basicConfig(level=logging.INFO)


def _parse(cloud_event) -> dict:
    data = cloud_event.data or {}
    msg = data.get("message", {})
    raw = msg.get("data")
    if not raw:
        return {}
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        log.warning("unparseable budget message")
        return {}


def _set_kill_switch(project: str, note: dict) -> bool:
    db = firestore.Client(project=project)
    ref = db.document("config/providers")
    snap = ref.get()
    before = snap.to_dict() if snap.exists else {}
    if before.get("limits", {}).get("kill_switch") is True:
        log.info("kill switch already on; nothing to do")
        return False
    now = dt.datetime.now(dt.UTC)
    after = json.loads(json.dumps(before, default=str))
    after.setdefault("limits", {})["kill_switch"] = True
    after["version"] = int(before.get("version", 0)) + 1
    after["updated_by"] = "budget-killswitch"
    after["updated_at"] = now.isoformat()
    batch = db.batch()
    batch.set(
        ref,
        {
            "limits": {"kill_switch": True},
            "version": after["version"],
            "updated_by": "budget-killswitch",
            "updated_at": now.isoformat(),
        },
        merge=True,
    )
    batch.set(
        db.collection("config_history").document(),
        {
            "doc": "providers",
            "before": before,
            "after": after,
            "actor": "budget-killswitch",
            "at": now,
            "budget": {
                k: note.get(k)
                for k in (
                    "budgetDisplayName",
                    "costAmount",
                    "budgetAmount",
                    "alertThresholdExceeded",
                    "costIntervalStart",
                )
            },
        },
    )
    batch.commit()
    log.warning(
        "kill switch set: cost %s >= budget %s", note.get("costAmount"), note.get("budgetAmount")
    )
    return True


def _repoint_twilio() -> None:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    number = os.environ.get("TWILIO_GUARDIAN_NUMBER", "")
    fallback = os.environ.get("FALLBACK_TWIML_URL", "")
    if not all([sid, token, number, fallback]) or "REPLACE_ME" in (sid, number, fallback):
        log.info("twilio env not configured; skipping number repoint")
        return
    try:
        from twilio.rest import Client
    except ImportError:
        log.warning("twilio package missing; skipping number repoint")
        return
    client = Client(sid, token)
    numbers = client.incoming_phone_numbers.list(phone_number=number, limit=1)
    if not numbers:
        log.warning("guardian number not found on account")
        return
    if numbers[0].voice_url == fallback:
        log.info("number already points at the fallback bin")
        return
    numbers[0].update(voice_url=fallback, voice_method="GET")
    log.warning("twilio number repointed to fallback bin")


@functions_framework.cloud_event
def on_budget(cloud_event) -> None:
    note = _parse(cloud_event)
    if not note:
        return
    cost = float(note.get("costAmount", 0) or 0)
    budget = float(note.get("budgetAmount", 0) or 0)
    log.info(
        "budget notice: cost=%s budget=%s threshold=%s",
        cost,
        budget,
        note.get("alertThresholdExceeded"),
    )
    if budget <= 0 or cost < budget:
        return
    project = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        log.error("GCP_PROJECT not set")
        return
    changed = _set_kill_switch(project, note)
    if changed:
        _repoint_twilio()
