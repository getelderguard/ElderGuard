"""Loads routing config and feature flags from YAML. A Firestore overlay slots in here later."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.providers.config import Flags, ProviderConfig


def load_provider_config(path: Path) -> ProviderConfig:
    data = yaml.safe_load(path.read_text()) or {}
    return ProviderConfig.model_validate(data)


def load_flags(path: Path) -> Flags:
    if not path.exists():
        return Flags()
    data = yaml.safe_load(path.read_text()) or {}
    return Flags.model_validate(data)
