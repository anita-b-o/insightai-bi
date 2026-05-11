MAX_BCRYPT_PASSWORD_BYTES = 72


def validate_bcrypt_password_bytes(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_BCRYPT_PASSWORD_BYTES} bytes when UTF-8 encoded"
        )
    return password
