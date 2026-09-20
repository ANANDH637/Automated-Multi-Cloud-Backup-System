"""AES-based (Fernet) file encryption derived from a user password."""
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_FILE = ".backup_salt"


def _get_salt(salt_path: str = SALT_FILE) -> bytes:
    if os.path.exists(salt_path):
        with open(salt_path, "rb") as f:
            return f.read()
    salt = os.urandom(16)
    with open(salt_path, "wb") as f:
        f.write(salt)
    return salt


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


class Encryptor:
    def __init__(self, password: str, salt_path: str = SALT_FILE):
        salt = _get_salt(salt_path)
        key = _derive_key(password, salt)
        self.fernet = Fernet(key)

    def encrypt_file(self, in_path: str, out_path: str) -> str:
        with open(in_path, "rb") as f:
            data = f.read()
        token = self.fernet.encrypt(data)
        with open(out_path, "wb") as f:
            f.write(token)
        return out_path

    def decrypt_file(self, in_path: str, out_path: str) -> str:
        with open(in_path, "rb") as f:
            token = f.read()
        data = self.fernet.decrypt(token)
        with open(out_path, "wb") as f:
            f.write(data)
        return out_path
