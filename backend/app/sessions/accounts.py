"""Account lookup by phone hash. Dev allow-list now, Firestore phone_index in M1."""

from __future__ import annotations

from typing import Protocol

from app.security.phone import last4, normalize_e164, phone_hash
from app.sessions.models import Account
from app.settings import Settings


class AccountResolver(Protocol):
    async def by_phone_hash(self, h: str) -> Account | None: ...


class DevAllowlistResolver:
    def __init__(self, settings: Settings) -> None:
        pepper = settings.phone_hash_pepper.get_secret_value()
        self._accounts: dict[str, Account] = {}
        for raw in settings.dev_allowed_phone_list:
            e164 = normalize_e164(raw)
            if not e164:
                continue
            h = phone_hash(e164, pepper)
            self._accounts[h] = Account(
                id="dev-" + last4(e164),
                phone_hash=h,
                senior_nickname="Mom",
                guardian_name="Jarmar",
                watch_list=["Medicare", "gift cards", "grandchild emergencies"],
            )

    async def by_phone_hash(self, h: str) -> Account | None:
        return self._accounts.get(h)
