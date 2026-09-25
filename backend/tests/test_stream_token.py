from app.security.stream_token import TOKEN_TTL_SECONDS, make_stream_token, verify_stream_token


def test_token_roundtrip():
    tok = make_stream_token("secret", "s_1", "CA1", now=1000.0)
    assert verify_stream_token("secret", tok, "s_1", "CA1", now=1001.0)


def test_token_bound_to_session_and_call():
    tok = make_stream_token("secret", "s_1", "CA1", now=1000.0)
    assert not verify_stream_token("secret", tok, "s_2", "CA1", now=1001.0)
    assert not verify_stream_token("secret", tok, "s_1", "CA2", now=1001.0)
    assert not verify_stream_token("other", tok, "s_1", "CA1", now=1001.0)


def test_token_expires():
    tok = make_stream_token("secret", "s_1", "CA1", now=1000.0)
    assert not verify_stream_token("secret", tok, "s_1", "CA1", now=1000.0 + TOKEN_TTL_SECONDS + 1)


def test_garbage_tokens():
    assert not verify_stream_token("secret", None, "s", "c")
    assert not verify_stream_token("secret", "nocolon", "s", "c")
    assert not verify_stream_token("secret", "abc:notanumber", "s", "c")
