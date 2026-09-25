"""Push notifications. Payloads never carry call content; the app fetches the session itself."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol

import structlog

from app.scoring.tiers import Tier
from app.sessions.accounts import AccountRepo
from app.sessions.models import Account, Guardian, InitiatedBy, Session

log = structlog.get_logger("notify")

GENERIC_BODY = "ElderGuard: open the app."


@dataclass(frozen=True)
class Push:
    uid: str
    kind: str  # tier_caution, tier_stop, no_audio, guardian_stop, guardian_linked, false_alarm
    session_id: str | None = None
    time_sensitive: bool = True


class PushSender(Protocol):
    async def send(self, token: str, push: Push) -> bool: ...


class LogPushSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Push]] = []

    async def send(self, token: str, push: Push) -> bool:
        self.sent.append((token, push))
        log.info("push", uid=push.uid, kind=push.kind, session_id=push.session_id)
        return True


class FcmPushSender:
    def __init__(self, project_id: str) -> None:
        import firebase_admin
        from firebase_admin import messaging

        self._messaging = messaging
        if not firebase_admin._apps:  # noqa: SLF001
            firebase_admin.initialize_app(options={"projectId": project_id})

    async def send(self, token: str, push: Push) -> bool:
        m = self._messaging
        data = {"kind": push.kind, "session_id": push.session_id or ""}
        apns_headers = {"apns-priority": "10"}
        aps = m.Aps(
            alert=m.ApsAlert(title="ElderGuard", body=GENERIC_BODY),
            sound="default",
            content_available=True,
        )
        if push.time_sensitive:
            apns_headers["apns-push-type"] = "alert"
            aps_payload = m.APNSPayload(aps=aps, **{"interruption-level": "time-sensitive"})
        else:
            aps_payload = m.APNSPayload(aps=aps)
        message = m.Message(
            token=token,
            notification=m.Notification(title="ElderGuard", body=GENERIC_BODY),
            data=data,
            android=m.AndroidConfig(
                priority="high",
                notification=m.AndroidNotification(channel_id="elderguard_alerts"),
            ),
            apns=m.APNSConfig(headers=apns_headers, payload=aps_payload),
        )
        try:
            await asyncio.to_thread(m.send, message)
            return True
        except Exception as e:  # noqa: BLE001 - never let a push failure touch a live call
            log.warning("push_failed", uid=push.uid, kind=push.kind, error=type(e).__name__)
            return False


class NotifyService:
    """Decides who gets told what. The sender just delivers."""

    def __init__(self, sender: PushSender, accounts: AccountRepo) -> None:
        self._sender = sender
        self._accounts = accounts

    async def _push(self, push: Push) -> None:
        device = await self._accounts.get_device(push.uid)
        if device is None:
            log.info("push_skipped_no_device", uid=push.uid, kind=push.kind)
            return
        await self._sender.send(device.fcm_token, push)

    async def tier_changed(
        self, session: Session, account: Account, old: Tier, new: Tier, *, guardian_alerts: bool
    ) -> None:
        if new == old:
            return
        if new in {Tier.CAUTION, Tier.STOP}:
            await self._push(Push(account.senior.uid, f"tier_{new.value}", session.id))
        if (
            new == Tier.STOP
            and session.initiated_by == InitiatedBy.APP
            and guardian_alerts
            and account.settings.alert_guardian
        ):
            now = time.time()
            for g in account.active_guardians(now):
                await self._push(Push(g.uid, "guardian_stop", session.id))

    async def no_audio(self, session: Session, account: Account) -> None:
        await self._push(Push(account.senior.uid, "no_audio", session.id))

    async def guardian_linked(self, account: Account, guardian: Guardian) -> None:
        targets = [account.senior.uid] + [g.uid for g in account.guardians if g.uid != guardian.uid]
        for uid in targets:
            await self._push(Push(uid, "guardian_linked", None, time_sensitive=False))

    async def session_ended_with_stop(self, session: Session, account: Account) -> None:
        await self._push(Push(account.senior.uid, "false_alarm", session.id, time_sensitive=False))
