from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, EncryptionError


def get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.fernet_key:
        raise ConfigurationError(
            "FERNET_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(settings.fernet_key.encode())
    except (ValueError, TypeError) as exc:
        raise ConfigurationError("FERNET_KEY is invalid.") from exc


def encrypt_value(plaintext: str) -> str:
    if not plaintext:
        return ""
    try:
        token = get_fernet().encrypt(plaintext.encode())
        return token.decode()
    except ConfigurationError:
        raise
    except Exception as exc:
        raise EncryptionError("Failed to encrypt value.") from exc


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        value = get_fernet().decrypt(ciphertext.encode())
        return value.decode()
    except InvalidToken as exc:
        raise EncryptionError("Failed to decrypt value — invalid token or key.") from exc
    except ConfigurationError:
        raise
    except Exception as exc:
        raise EncryptionError("Failed to decrypt value.") from exc
