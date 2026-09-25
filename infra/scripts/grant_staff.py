#!/usr/bin/env python3
"""Grant or revoke the `staff` custom claim on a Firebase user.

  grant_staff.py --project my-proj UID
  grant_staff.py --project my-proj UID --revoke

`staff: true` unlocks GET /admin/usage. It is never set from the app. The user must sign out
and back in (or refresh their ID token) for the claim to take effect.
"""

from __future__ import annotations

import argparse
import sys

from _common import project_from_args_or_env


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--project")
    p.add_argument("uid")
    p.add_argument("--revoke", action="store_true")
    args = p.parse_args()
    project = project_from_args_or_env(args.project)

    import firebase_admin
    from firebase_admin import auth

    firebase_admin.initialize_app(options={"projectId": project})
    user = auth.get_user(args.uid)
    claims = dict(user.custom_claims or {})
    if args.revoke:
        claims.pop("staff", None)
    else:
        claims["staff"] = True
    auth.set_custom_user_claims(args.uid, claims or None)
    phone_tail = (user.phone_number or "")[-4:]
    print(f"{'revoked' if args.revoke else 'granted'} staff on {args.uid} (phone ...{phone_tail})")
    print("claims now:", claims or {})
    return 0


if __name__ == "__main__":
    sys.exit(main())
