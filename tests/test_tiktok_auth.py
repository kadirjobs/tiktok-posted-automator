from app.services.tiktok.auth import TikTokAuthService


def test_pkce_pair_generation() -> None:
    verifier, challenge = TikTokAuthService._generate_pkce_pair()
    assert len(verifier) > 20
    assert len(challenge) > 20
    assert "=" not in challenge
