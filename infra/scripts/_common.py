"""Shared helpers for operator scripts. Imports the backend's models by path so validation
matches what the service enforces. Nothing here touches secrets."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"


def add_backend_to_path() -> None:
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))


def gcloud_account() -> str:
    """The operator identity recorded in config_history. Falls back to $USER."""
    try:
        out = subprocess.run(
            ["gcloud", "config", "get-value", "account"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        acct = out.stdout.strip()
        if acct and acct != "(unset)":
            return acct
    except (OSError, subprocess.SubprocessError):
        pass
    return os.environ.get("USER", "unknown")


def project_from_args_or_env(explicit: str | None) -> str:
    project = explicit or os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        sys.exit("pass --project or set GCP_PROJECT")
    return project
