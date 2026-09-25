"""TwiML for the Guardian Line. The only place call-flow XML is built."""

from __future__ import annotations

from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

FALLBACK_NOTICE = (
    "ElderGuard can't listen right now. If anything about this call feels wrong, hang up. "
    "Never give codes or payment over the phone."
)

PRE_MERGE_INSTRUCTION = (
    "It's ElderGuard. Now press the Merge Calls button on your screen. I'll listen with you."
)


def reject() -> str:
    resp = VoiceResponse()
    resp.reject(reason="rejected")
    return str(resp)


def guardian_line(
    *,
    ws_url: str,
    session_id: str,
    token: str,
    redirect_url: str,
    status_callback_url: str,
    instruction_text: str | None = PRE_MERGE_INSTRUCTION,
    instruction_audio_url: str | None = None,
) -> str:
    """Spoken instruction, then a bidirectional media stream, then the reconnect redirect."""
    resp = VoiceResponse()
    if instruction_audio_url:
        resp.play(instruction_audio_url)
    elif instruction_text:
        resp.say(instruction_text)
    connect = Connect()
    stream = Stream(
        url=ws_url,
        status_callback=status_callback_url,
        status_callback_method="POST",
    )
    stream.parameter(name="sid", value=session_id)
    stream.parameter(name="tok", value=token)
    connect.append(stream)
    resp.append(connect)
    resp.redirect(redirect_url, method="POST")
    return str(resp)


def fallback_notice(text: str = FALLBACK_NOTICE) -> str:
    resp = VoiceResponse()
    resp.say(text)
    resp.hangup()
    return str(resp)
