from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _fernet() -> Fernet:
    key = current_app.config["FERNET_KEY"]
    # Ensure key is valid url-safe base64 32-byte key
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_trn(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_trn(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt TRN") from exc
