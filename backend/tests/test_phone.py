from app.security.phone import normalize_e164, phone_hash


def test_normalize_variants():
    assert normalize_e164("(415) 555-0142") == "+14155550142"
    assert normalize_e164("14155550142") == "+14155550142"
    assert normalize_e164("+14155550142") == "+14155550142"
    assert normalize_e164("+442071234567") == "+442071234567"


def test_anonymous_and_garbage():
    assert normalize_e164("") is None
    assert normalize_e164(None) is None
    assert normalize_e164("anonymous") is None
    assert normalize_e164("+266696687") is None
    assert normalize_e164("123") is None


def test_hash_depends_on_pepper():
    a = phone_hash("+14155550142", "p1")
    b = phone_hash("+14155550142", "p2")
    assert a != b and len(a) == 64
