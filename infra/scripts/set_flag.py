#!/usr/bin/env python3
"""Flip a feature flag in the Firestore config overlay (config/flags).

Examples:
  set_flag.py --project my-proj announcement off
  set_flag.py --project my-proj takeover on
  set_flag.py --project my-proj --show

Flags are validated against backend/app/providers/config.py::Flags so a typo cannot create a
flag the backend ignores. Every change is appended to config_history with the operator's
gcloud account.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from _common import BACKEND, add_backend_to_path, gcloud_account, project_from_args_or_env

add_backend_to_path()

from app.providers.config import Flags  # noqa: E402
from app.providers.loader import load_flags  # noqa: E402

FLAG_NAMES = sorted(Flags.model_fields)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--project")
    p.add_argument("flag", nargs="?", choices=FLAG_NAMES)
    p.add_argument("value", nargs="?", choices=["on", "off"])
    p.add_argument("--show", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    project = project_from_args_or_env(args.project)
    from google.cloud import firestore

    db = firestore.Client(project=project)
    seed = load_flags(BACKEND / "config" / "flags.default.yaml").model_dump()
    snap = db.document("config/flags").get()
    overlay = snap.to_dict() if snap.exists else {}
    merged = {**seed, **{k: v for k, v in overlay.items() if k in seed}}

    if args.show:
        print(json.dumps(merged, indent=2))
        return 0
    if not (args.flag and args.value):
        p.error("give FLAG on|off, or --show")

    new_overlay = dict(overlay)
    new_overlay[args.flag] = args.value == "on"
    Flags.model_validate({**seed, **{k: v for k, v in new_overlay.items() if k in seed}})

    actor = gcloud_account()
    now = dt.datetime.now(dt.UTC)
    new_overlay["updated_by"] = actor
    new_overlay["updated_at"] = now.isoformat()
    print(f"{args.flag}: {merged.get(args.flag)} -> {new_overlay[args.flag]}")
    if args.dry_run:
        print("dry-run: not writing")
        return 0

    batch = db.batch()
    batch.set(db.document("config/flags"), new_overlay)
    batch.set(
        db.collection("config_history").document(),
        {"doc": "flags", "before": overlay, "after": new_overlay, "actor": actor, "at": now},
    )
    batch.commit()
    print(f"written by {actor}; the service picks it up within CONFIG_CACHE_SECONDS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
