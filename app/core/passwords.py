from passlib.context import CryptContext

# bcrypt 有 72 bytes 限制；pbkdf2_sha256 没这个限制，先保证项目跑通
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(raw: str) -> str:
    # 防御：确保是字符串
    if raw is None:
        raise ValueError("password is None")
    return pwd_context.hash(str(raw))


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(str(raw), hashed)
