from app.telephony.codec import mulaw_to_pcm16, pcm16_to_mulaw, silence, upsample_2x


def test_roundtrip_is_close():
    import struct

    samples = [0, 100, -100, 1000, -1000, 8000, -8000, 30000, -30000]
    pcm = b"".join(struct.pack("<h", s) for s in samples)
    back = mulaw_to_pcm16(pcm16_to_mulaw(pcm))
    decoded = struct.unpack(f"<{len(samples)}h", back)
    for orig, got in zip(samples, decoded, strict=True):
        assert abs(orig - got) <= max(64, abs(orig) * 0.07)


def test_silence_decodes_to_zero():
    pcm = mulaw_to_pcm16(silence(0.01))
    assert set(pcm) == {0}


def test_upsample_doubles_length():
    pcm = mulaw_to_pcm16(silence(0.01))
    assert len(upsample_2x(pcm)) == 2 * len(pcm)
