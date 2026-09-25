"""Account repository: seniors, guardians, invites, devices. Memory and Firestore back ends."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Protocol

import structlog

from app.security.phone import last4, normalize_e164, phone_hash
from app.sessions.models import (
    GUARDIAN_COOL_OFF_S,
    Account,
    AccountSettings,
    Device,
    Guardian,
    GuardianInvite,
    Senior,
)
from app.settings import Settings

log = structlog.get_logger("accounts")


class AccountError(Exception):
    pass


class AlreadyEnrolled(AccountError):
    pass


class NotFound(AccountError):
    pass


class AccountRepo(Protocol):
    async def by_phone_hash(self, h: str) -> Account | None: ...

    async def get(self, account_id: str) -> Account | None: ...

    async def for_senior_uid(self, uid: str) -> Account | None: ...

    async def guarded_by(self, uid: str) -> list[Account]: ...

    async def create(self, account: Account) -> Account: ...

    async def update(self, account_id: str, **fields: Any) -> Account: ...

    async def create_invite(self, invite: GuardianInvite) -> GuardianInvite: ...

    async def open_invite_for_phone(self, h: str, now: float) -> GuardianInvite | None: ...

    async def claim_invite(self, invite_id: str, uid: str, now: float) -> None: ...

    async def put_device(self, device: Device) -> None: ...

    async def get_device(self, uid: str) -> Device | None: ...

    async def delete_device(self, uid: str) -> None: ...

    async def delete_account(self, account_id: str) -> None: ...

    async def record_deletion(self, record: dict[str, Any]) -> None: ...


class InMemoryAccountRepo:
    """Dev and test back end. Seeds enrolled seniors from DEV_ALLOWED_PHONES."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._accounts: dict[str, Account] = {}
        self._phone_index: dict[str, tuple[str, str, str]] = {}  # hash -> (account_id, role, uid)
        self._invites: dict[str, GuardianInvite] = {}
        self._devices: dict[str, Device] = {}
        self.deletions: list[dict[str, Any]] = []
        if settings is not None:
            self._seed(settings)

    def _seed(self, settings: Settings) -> None:
        pepper = settings.phone_hash_pepper.get_secret_value()
        for raw in settings.dev_allowed_phone_list:
            e164 = normalize_e164(raw)
            if not e164:
                continue
            h = phone_hash(e164, pepper)
            uid = "dev-" + last4(e164)
            acct = Account(
                id=uid,
                phone_hash=h,
                senior=Senior(
                    uid=uid,
                    display_name="Dev Senior",
                    nickname="Mom",
                    phone_last4=last4(e164),
                    consent_version="dev",
                    consent_at=time.time(),
                ),
                guardians=[
                    Guardian(uid="dev-guardian", name="Jarmar", relationship="son", active_at=0.0)
                ],
                guardian_uids=["dev-guardian"],
                watch_list=["Medicare", "gift cards", "grandchild emergencies"],
            )
            self._accounts[uid] = acct
            self._phone_index[h] = (uid, "senior", uid)

    async def by_phone_hash(self, h: str) -> Account | None:
        row = self._phone_index.get(h)
        if row is None or row[1] != "senior":
            return None
        return self._accounts.get(row[0])

    async def get(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    async def for_senior_uid(self, uid: str) -> Account | None:
        return self._accounts.get(uid)

    async def guarded_by(self, uid: str) -> list[Account]:
        return [a for a in self._accounts.values() if uid in a.guardian_uids]

    async def create(self, account: Account) -> Account:
        if account.id in self._accounts or account.phone_hash in self._phone_index:
            raise AlreadyEnrolled(account.id)
        self._accounts[account.id] = account
        self._phone_index[account.phone_hash] = (account.id, "senior", account.senior.uid)
        return account

    async def update(self, account_id: str, **fields: Any) -> Account:
        current = self._accounts.get(account_id)
        if current is None:
            raise NotFound(account_id)
        data = current.model_dump()
        data.update(fields)
        data["updated_at"] = time.time()
        updated = Account.model_validate(data)
        self._accounts[account_id] = updated
        return updated

    async def create_invite(self, invite: GuardianInvite) -> GuardianInvite:
        self._invites[invite.id] = invite
        return invite

    async def open_invite_for_phone(self, h: str, now: float) -> GuardianInvite | None:
        for inv in reversed(list(self._invites.values())):
            if inv.phone_hash == h and inv.claimed_at is None and inv.expires_at > now:
                return inv
        return None

    async def claim_invite(self, invite_id: str, uid: str, now: float) -> None:
        inv = self._invites[invite_id]
        self._invites[invite_id] = inv.model_copy(update={"claimed_at": now, "claimed_uid": uid})

    async def put_device(self, device: Device) -> None:
        self._devices[device.uid] = device

    async def get_device(self, uid: str) -> Device | None:
        return self._devices.get(uid)

    async def delete_device(self, uid: str) -> None:
        self._devices.pop(uid, None)

    async def delete_account(self, account_id: str) -> None:
        acct = self._accounts.pop(account_id, None)
        if acct is None:
            return
        self._phone_index.pop(acct.phone_hash, None)
        self._devices.pop(acct.senior.uid, None)
        for inv_id in [i for i, inv in self._invites.items() if inv.account_id == account_id]:
            self._invites.pop(inv_id, None)

    async def record_deletion(self, record: dict[str, Any]) -> None:
        self.deletions.append(record)


class AccountService:
    """Business rules on top of the repo. Routers call this, never the repo directly."""

    def __init__(self, repo: AccountRepo, settings: Settings) -> None:
        self.repo = repo
        self._pepper = settings.phone_hash_pepper.get_secret_value()

    def hash_phone(self, e164: str) -> str:
        return phone_hash(e164, self._pepper)

    async def enroll(
        self,
        *,
        uid: str,
        phone_e164: str,
        display_name: str,
        nickname: str,
        consent_version: str,
        watch_list: list[str],
    ) -> Account:
        now = time.time()
        acct = Account(
            id=uid,
            phone_hash=self.hash_phone(phone_e164),
            senior=Senior(
                uid=uid,
                display_name=display_name,
                nickname=nickname or "Mom",
                phone_last4=last4(phone_e164),
                consent_version=consent_version,
                consent_at=now,
            ),
            watch_list=watch_list,
            settings=AccountSettings(),
            created_at=now,
            updated_at=now,
        )
        created = await self.repo.create(acct)
        log.info("account_enrolled", account_id=created.id)
        return created

    async def invite_guardian(
        self, account: Account, *, phone_e164: str, name: str, relationship: str
    ) -> GuardianInvite:
        h = self.hash_phone(phone_e164)
        if h == account.phone_hash:
            raise AccountError("a senior cannot be their own guardian")
        inv = GuardianInvite(
            account_id=account.id, phone_hash=h, name=name, relationship=relationship
        )
        await self.repo.create_invite(inv)
        log.info("guardian_invited", account_id=account.id, invite_id=inv.id)
        return inv

    async def link_guardian(self, *, uid: str, phone_e164: str) -> tuple[Account, Guardian]:
        """Called from the guardian's own device. Cool-off applies before they go live."""
        now = time.time()
        h = self.hash_phone(phone_e164)
        inv = await self.repo.open_invite_for_phone(h, now)
        if inv is None:
            raise NotFound("no open invite for this phone")
        account = await self.repo.get(inv.account_id)
        if account is None:
            raise NotFound(inv.account_id)
        if uid == account.senior.uid:
            raise AccountError("the senior cannot link as their own guardian")
        guardian = Guardian(
            uid=uid,
            name=inv.name,
            relationship=inv.relationship,
            phone_last4=last4(phone_e164),
            linked_at=now,
            active_at=now + GUARDIAN_COOL_OFF_S,
        )
        guardians = [g for g in account.guardians if g.uid != uid] + [guardian]
        account = await self.repo.update(
            account.id,
            guardians=[g.model_dump() for g in guardians],
            guardian_uids=sorted({g.uid for g in guardians}),
        )
        await self.repo.claim_invite(inv.id, uid, now)
        log.info("guardian_linked", account_id=account.id, active_at=guardian.active_at)
        return account, guardian

    async def delete_account(self, account: Account, *, reason: str) -> None:
        """The order matters: sessions first, then the account and its index, then the record."""
        await self.repo.delete_account(account.id)
        await self.repo.record_deletion(
            {
                "at": time.time(),
                "account_hash": hashlib.sha256(account.id.encode()).hexdigest(),
                "consent_version": account.senior.consent_version,
                "reason": reason,
            }
        )
        log.info("account_deleted", account_id=account.id, reason=reason)

    async def remove_guardian(self, account: Account, uid: str) -> Account:
        guardians = [g for g in account.guardians if g.uid != uid]
        if len(guardians) == len(account.guardians):
            raise NotFound(uid)
        account = await self.repo.update(
            account.id,
            guardians=[g.model_dump() for g in guardians],
            guardian_uids=sorted({g.uid for g in guardians}),
        )
        log.info("guardian_removed", account_id=account.id)
        return account
