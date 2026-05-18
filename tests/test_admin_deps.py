from app.api.deps import hash_admin_password, verify_admin_password


def test_password_hash_roundtrip() -> None:
    hashed = hash_admin_password("test-password-123")
    assert verify_admin_password("test-password-123", hashed)
    assert not verify_admin_password("wrong", hashed)
