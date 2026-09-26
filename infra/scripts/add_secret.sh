#!/usr/bin/env bash
# Add a Secret Manager version without the value touching the shell, the
# clipboard history, or a chat transcript.
#
#   infra/scripts/add_secret.sh SECRET_NAME [--project PROJECT]
#
# Interactive terminal: opens an empty editor window, waits for Enter, then
# uploads. Non-interactive (for example a chat-driven shell): two calls.
#
#   add_secret.sh SECRET_NAME --open     creates the file and opens it in TextEdit
#   add_secret.sh SECRET_NAME --commit   uploads the saved value and shreds the file
#
# Whitespace is stripped so a trailing newline from the editor is harmless.
set -euo pipefail

NAME="${1:?usage: add_secret.sh SECRET_NAME [--project PROJECT] [--open|--commit]}"; shift
PROJECT="${GCP_PROJECT:-}"
MODE="auto"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --open) MODE="open"; shift ;;
    --commit) MODE="commit"; shift ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done
PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
[[ -n "$PROJECT" ]] || { echo "set --project or GCP_PROJECT" >&2; exit 1; }

DIR="${XDG_CONFIG_HOME:-$HOME/.config}/elderguard"
mkdir -p "$DIR" && chmod 700 "$DIR"
FILE="$DIR/pending-${NAME}.txt"

shred_file() { rm -P -f "$FILE" 2>/dev/null || rm -f "$FILE"; }

open_editor() {
  : > "$FILE"
  chmod 600 "$FILE"
  if [[ "$(uname)" == "Darwin" ]]; then
    open -e "$FILE"
  else
    "${EDITOR:-vi}" "$FILE"
  fi
}

commit_value() {
  [[ -f "$FILE" ]] || { echo "no pending file for ${NAME}; run with --open first" >&2; exit 1; }
  local value len
  value="$(tr -d '[:space:]' < "$FILE")"
  if [[ -z "$value" ]]; then
    shred_file
    echo "the file was empty; nothing added. Run --open again." >&2
    exit 1
  fi
  len=${#value}
  printf '%s' "$value" | gcloud secrets versions add "$NAME" --project="$PROJECT" --data-file=- --format='value(name)'
  unset value
  shred_file
  echo "added a ${len}-character value to ${NAME}"
}

if [[ "$MODE" == "auto" ]]; then
  if [[ -t 0 ]]; then
    trap shred_file EXIT
    open_editor
    echo "TextEdit is open. Paste the value for ${NAME}, save (Cmd-S), close the window, then press Enter here."
    read -r -p "> " _
    commit_value
  else
    MODE="open"
  fi
fi

case "$MODE" in
  open)
    open_editor
    echo "TextEdit is open. Paste the value for ${NAME}, save (Cmd-S), close the window, then run:"
    echo "  $0 ${NAME} --project ${PROJECT} --commit"
    ;;
  commit) commit_value ;;
esac
