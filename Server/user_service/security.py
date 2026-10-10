import hashlib
import hmac
import secrets


_HASH_SCHEME = "pbkdf2_sha256"
_HASH_ITERATIONS = 600_000
_SALT_LENGTH = 16
_MIN_HASH_ITERATIONS = 100_000
_MAX_HASH_ITERATIONS = 2_000_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_LENGTH)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _HASH_ITERATIONS,
    )
    return f"{_HASH_SCHEME}${_HASH_ITERATIONS}${salt.hex()}${password_hash.hex()}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        scheme, iteration_text, salt_text, expected_hash = stored_password.split("$")
        iterations = int(iteration_text)
        if (
            scheme != _HASH_SCHEME
            or not _MIN_HASH_ITERATIONS <= iterations <= _MAX_HASH_ITERATIONS
        ):
            return False
        salt = bytes.fromhex(salt_text)
        if len(salt) != _SALT_LENGTH:
            return False
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        ).hex()
        return hmac.compare_digest(actual_hash, expected_hash)
    except (ValueError, TypeError):
        return hmac.compare_digest(password.encode("utf-8"), stored_password.encode("utf-8"))


def is_hashed_password(stored_password: str) -> bool:
    return stored_password.startswith(f"{_HASH_SCHEME}$")
