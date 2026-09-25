from app.telephony import twiml


def test_guardian_line_shape():
    xml = twiml.guardian_line(
        ws_url="wss://api.example.test/twilio/media",
        session_id="s_abc",
        token="deadbeef:123",
        redirect_url="https://api.example.test/twilio/voice/reconnect",
        status_callback_url="https://api.example.test/twilio/voice/stream-status",
    )
    assert "<Say>" in xml
    assert "<Connect>" in xml
    assert 'url="wss://api.example.test/twilio/media"' in xml
    assert 'statusCallback="https://api.example.test/twilio/voice/stream-status"' in xml
    assert '<Parameter name="sid" value="s_abc"' in xml
    assert '<Parameter name="tok" value="deadbeef:123"' in xml
    assert xml.index("</Connect>") < xml.index("<Redirect")
    assert "reconnect</Redirect>" in xml


def test_reconnect_has_no_instruction():
    xml = twiml.guardian_line(
        ws_url="wss://x/twilio/media",
        session_id="s",
        token="t",
        redirect_url="https://x/r",
        status_callback_url="https://x/s",
        instruction_text=None,
    )
    assert "<Say>" not in xml


def test_reject_and_fallback():
    assert '<Reject reason="rejected"' in twiml.reject()
    fb = twiml.fallback_notice()
    assert "<Say>" in fb and "<Hangup" in fb
    assert "safe" not in fb.lower()
