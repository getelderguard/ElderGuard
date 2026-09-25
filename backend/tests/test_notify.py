"""Who gets a push, and when. Payloads are generic; only the kind and session id vary."""

from __future__ import annotations

import asyncio
import time

from app.notify.push import LogPushSender, NotifyService
from app.scoring.tiers import Tier
from app.sessions.accounts import InMemoryAccountRepo
from app.sessions.models import (
    Account,
    AccountSettings,
    Device,
    Guardian,
    InitiatedBy,
    Senior,
    Session,
)


def _account(guardian_active: bool, alert_guardian: bool = True) -> Account:
    active_at = time.time() - 10 if guardian_active else time.time() + 3600
    return Account(
        id="mom",
        phone_hash="h",
        senior=Senior(uid="mom", nickname="Mom"),
        guardians=[Guardian(uid="kid", name="Kid", active_at=active_at)],
        guardian_uids=["kid"],
        settings=AccountSettings(alert_guardian=alert_guardian),
    )


def _setup(account: Account):
    repo = InMemoryAccountRepo()
    sender = LogPushSender()
    svc = NotifyService(sender, repo)
    asyncio.run(repo.put_device(Device(uid="mom", fcm_token="m" * 40)))
    asyncio.run(repo.put_device(Device(uid="kid", fcm_token="k" * 40)))
    return svc, sender


def _session(initiated_by=InitiatedBy.APP) -> Session:
    return Session(id="s1", account_id="mom", phone_hash="h", initiated_by=initiated_by)


def test_caution_pushes_senior_only():
    acct = _account(guardian_active=True)
    svc, sender = _setup(acct)
    asyncio.run(
        svc.tier_changed(_session(), acct, Tier.LISTENING, Tier.CAUTION, guardian_alerts=True)
    )
    assert [(p.uid, p.kind) for _, p in sender.sent] == [("mom", "tier_caution")]


def test_stop_pushes_senior_and_active_guardian():
    acct = _account(guardian_active=True)
    svc, sender = _setup(acct)
    asyncio.run(svc.tier_changed(_session(), acct, Tier.CAUTION, Tier.STOP, guardian_alerts=True))
    kinds = sorted((p.uid, p.kind) for _, p in sender.sent)
    assert kinds == [("kid", "guardian_stop"), ("mom", "tier_stop")]


def test_stop_skips_guardian_in_cool_off_or_when_disabled():
    for acct in (_account(guardian_active=False), _account(True, alert_guardian=False)):
        svc, sender = _setup(acct)
        asyncio.run(
            svc.tier_changed(_session(), acct, Tier.CAUTION, Tier.STOP, guardian_alerts=True)
        )
        assert [p.uid for _, p in sender.sent] == ["mom"]
    acct = _account(guardian_active=True)
    svc, sender = _setup(acct)
    asyncio.run(svc.tier_changed(_session(), acct, Tier.CAUTION, Tier.STOP, guardian_alerts=False))
    assert [p.uid for _, p in sender.sent] == ["mom"]


def test_line_initiated_stop_never_alerts_guardian():
    """A spoofed caller cannot page the family by dialing the line and reading scam lines."""
    acct = _account(guardian_active=True)
    svc, sender = _setup(acct)
    asyncio.run(
        svc.tier_changed(
            _session(InitiatedBy.LINE), acct, Tier.CAUTION, Tier.STOP, guardian_alerts=True
        )
    )
    assert [p.uid for _, p in sender.sent] == ["mom"]


def test_same_tier_and_downgrades_are_silent():
    acct = _account(guardian_active=True)
    svc, sender = _setup(acct)
    asyncio.run(svc.tier_changed(_session(), acct, Tier.STOP, Tier.STOP, guardian_alerts=True))
    asyncio.run(svc.tier_changed(_session(), acct, Tier.STOP, Tier.CAUTION, guardian_alerts=True))
    asyncio.run(
        svc.tier_changed(_session(), acct, Tier.CAUTION, Tier.LISTENING, guardian_alerts=True)
    )
    assert [p.kind for _, p in sender.sent] == ["tier_caution"]


def test_no_device_means_no_push():
    acct = _account(guardian_active=True)
    repo = InMemoryAccountRepo()
    sender = LogPushSender()
    svc = NotifyService(sender, repo)
    asyncio.run(svc.no_audio(_session(), acct))
    assert sender.sent == []
