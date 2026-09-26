#!/usr/bin/env bash
# Add a Secret Manager version without the value touching the shell, the
# clipboard, or a chat transcript. Opens an empty TextEdit window; paste the
# value there, save, close, then press Enter here. Whitespace is stripped and
# the temp file is shredded.
#
#   infra/scripts/add_secret.sh SECRET_NAME [--project PROJECT]
set -euo pipefail

NAME="${1:?usage: add_secret.sh SECRET_NAME [--project PROJECT]}"; shift
PROJECT="${GCP_PROJECT:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done
PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
[[ -n "$PROJECT" ]] || { echo "set --project or GCP_PROJECT" >&2; exit 1; }

TMP="$(mktemp -t elderguard-secret).txt"
trap 'rm -P -f "$TMP" 2>/dev/null || rm -f "$TMP"' EXIT
: > "$TMP"
chmod 600 "$TMP"

if [[ "$(uname)" == "Darwin" ]]; then
  open -e "$TMP"
  echo "TextEdit is open. Paste the value for ${NAME}, save (Cmd-S), close the window, then press Enter here."
else
  "${EDITOR:-vi}" "$TMP"
fi
read -r -p "> " _

VALUE="$(tr -d '[:space:]' < "$TMP")"
[[ -n "$VALUE" ]] || { echo "the file was empty; nothing added" >&2; exit 1; }
LEN=${#VALUE}
printf '%s' "$VALUE" | gcloud secrets versions add "$NAME" --project="$PROJECT" --data-file=- --format='value(name)'
unset VALUE
echo "added a ${LEN}-character value to ${NAME}"
