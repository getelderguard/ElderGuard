#!/usr/bin/env bash
# Rotate one Secret Manager secret: add a new version from stdin, disable every older version,
# and print the redeploy command. The value is never echoed and never passed as an argument.
#
#   cat /path/to/new-value.txt | infra/scripts/rotate_secret.sh --project my-proj ANTHROPIC_API_KEY
#   python3 -c 'import secrets; print(secrets.token_hex(32))' | infra/scripts/rotate_secret.sh --project my-proj STREAM_TOKEN_SECRET
#
# Refuses to run when stdin is a terminal so a secret is never typed into shell history.
# Note on PHONE_HASH_PEPPER: rotating it orphans every phone_index row. See docs/RUNBOOK.md.

set -euo pipefail

PROJECT=""
REGION="us-central1"
SECRET=""
DESTROY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --destroy-old) DESTROY=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    -*) echo "unknown flag: $1" >&2; exit 1 ;;
    *) SECRET="$1"; shift ;;
  esac
done

[[ -n "$PROJECT" && -n "$SECRET" ]] || { echo "usage: rotate_secret.sh --project P [--region R] [--destroy-old] SECRET_NAME" >&2; exit 1; }

if [[ -t 0 ]]; then
  echo "refusing: stdin is a terminal. Pipe the value in from a file or a password manager." >&2
  exit 2
fi

if [[ "$SECRET" == "PHONE_HASH_PEPPER" ]]; then
  echo "WARNING: rotating PHONE_HASH_PEPPER invalidates every phone_index entry. Re-enrolment required." >&2
  echo "         Continuing in 5 seconds; Ctrl-C to abort." >&2
  sleep 5
fi

NEW_VERSION="$(gcloud secrets versions add "$SECRET" --project="$PROJECT" --data-file=- --format='value(name)')"
NEW_ID="${NEW_VERSION##*/}"
echo "added ${SECRET} version ${NEW_ID}"

while read -r ver state; do
  [[ "$ver" == "$NEW_ID" ]] && continue
  [[ "$state" == "ENABLED" ]] || continue
  if [[ "$DESTROY" -eq 1 ]]; then
    gcloud secrets versions destroy "$ver" --secret="$SECRET" --project="$PROJECT" --quiet
    echo "destroyed version ${ver}"
  else
    gcloud secrets versions disable "$ver" --secret="$SECRET" --project="$PROJECT" --quiet
    echo "disabled version ${ver} (use --destroy-old after the new version is confirmed working)"
  fi
done < <(gcloud secrets versions list "$SECRET" --project="$PROJECT" --format='value(name,state)')

cat <<EOF

Cloud Run reads ':latest' at instance start. Roll the service to pick it up:
  gcloud run services update elderguard-api --region=${REGION} --project=${PROJECT} --update-env-vars=ROTATED_AT=$(date -u +%Y%m%dT%H%M%SZ)
Then check /ready and, if the old version was only disabled, destroy it:
  gcloud secrets versions destroy OLD_ID --secret=${SECRET} --project=${PROJECT}
EOF
