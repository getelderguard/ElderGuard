#!/usr/bin/env python3
"""Switch a capability's primary provider in the Firestore config overlay.

Examples:
  set_provider.py --project my-proj scorer anthropic claude-sonnet-5
  set_provider.py --project my-proj transcriber deepgram nova-3 --fallback google_stt
  set_provider.py --project my-proj --kill-switch on
  set_provider.py --project my-proj --show

The backend merges config/providers over backend/config/providers.default.yaml and re-reads it
every CONFIG_CACHE_SECONDS. Every change is appended to config_history with the operator's
gcloud account. Runs as your ADC identity; no service-account keys.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from _common import add_backend_to_path, gcloud_account, project_from_args_or_env

add_backend_to_path()

from _common import BACKEND  # noqa: E402

from app.providers.config import (  # noqa: E402
    CAPABILITIES,
    CapabilityRouting,
    ProviderConfig,
    Route,
)
from app.providers.loader import load_provider_config  # noqa: E402


def _client(project: str):
    from google.cloud import firestore

    return firestore.Client(project=project)


def _current(db, seed: ProviderConfig) -> dict:
    snap = db.document("config/providers").get()
    overlay = snap.to_dict() if snap.exists else {}
    merged = seed.model_dump()
    for key in ("capabilities", "limits"):
        if key in overlay:
            if isinstance(merged.get(key), dict) and isinstance(overlay[key], dict):
                merged[key].update(overlay[key])
            else:
                merged[key] = overlay[key]
    return merged, overlay


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--project")
    p.add_argument("capability", nargs="?", choices=CAPABILITIES)
    p.add_argument("provider", nargs="?")
    p.add_argument("model", nargs="?", default="")
    p.add_argument("--fallback", action="append", default=[], help="fallback provider, repeatable")
    p.add_argument("--params", default="{}", help="JSON params for the route")
    p.add_argument("--kill-switch", choices=["on", "off"])
    p.add_argument("--show", action="store_true", help="print the merged config and exit")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    project = project_from_args_or_env(args.project)
    seed = load_provider_config(BACKEND / "config" / "providers.default.yaml")
    db = _client(project)
    merged, overlay = _current(db, seed)

    if args.show:
        print(json.dumps(merged, indent=2, default=str))
        return 0

    new_overlay = json.loads(json.dumps(overlay))
    if args.kill_switch:
        new_overlay.setdefault("limits", {})["kill_switch"] = args.kill_switch == "on"
    elif args.capability and args.provider:
        routing = CapabilityRouting(
            routes=[
                Route(
                    provider=args.provider,
                    model=args.model,
                    weight=100,
                    params=json.loads(args.params),
                )
            ]
            + [Route(provider=f, model="", weight=0) for f in args.fallback],
            fallback_order=list(args.fallback),
        )
        new_overlay.setdefault("capabilities", {})[args.capability] = routing.model_dump()
    else:
        p.error("give CAPABILITY PROVIDER [MODEL], or --kill-switch, or --show")

    # Validate the merged result the same way the backend will.
    candidate = json.loads(json.dumps(merged))
    for key, val in new_overlay.items():
        if isinstance(candidate.get(key), dict) and isinstance(val, dict):
            candidate[key].update(val)
        else:
            candidate[key] = val
    ProviderConfig.model_validate(candidate)

    actor = gcloud_account()
    now = dt.datetime.now(dt.UTC)
    new_overlay["version"] = int(overlay.get("version", 0)) + 1
    new_overlay["updated_by"] = actor
    new_overlay["updated_at"] = now.isoformat()

    print("before:", json.dumps(overlay, indent=2, default=str))
    print("after: ", json.dumps(new_overlay, indent=2, default=str))
    if args.dry_run:
        print("dry-run: not writing")
        return 0

    batch = db.batch()
    batch.set(db.document("config/providers"), new_overlay)
    batch.set(
        db.collection("config_history").document(),
        {"doc": "providers", "before": overlay, "after": new_overlay, "actor": actor, "at": now},
    )
    batch.commit()
    print(f"written by {actor}; the service picks it up within CONFIG_CACHE_SECONDS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
