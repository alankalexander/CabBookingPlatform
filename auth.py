import hashlib, hmac, os, time
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from .config import settings
from .db import get_session
from .models import User

bearer = HTTPBearer()

def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return f"{salt.hex()}:{dk.hex()}"

def check_password(pw: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000)
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False

def make_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": int(time.time()) + 7 * 86400},
                      settings.secret_key, algorithm="HS256")

def decode_token(token: str) -> dict:
    claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if "purpose" in claims:                    # reset/verify tokens can't be used to log in
        raise jwt.InvalidTokenError("not a login token")
    return claims

def make_purpose_token(user_id: str, purpose: str, minutes: int, extra: dict | None = None) -> str:
    payload = {"sub": user_id, "purpose": purpose, "exp": int(time.time()) + minutes * 60, **(extra or {})}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def read_purpose_token(token: str, purpose: str) -> dict:
    claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if claims.get("purpose") != purpose:
        raise jwt.InvalidTokenError("wrong token type")
    return claims

def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer),
                 s: Session = Depends(get_session)) -> User:
    try:
        claims = decode_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = s.get(User, claims["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    return user

def require_role(role: str):
    def dep(u: User = Depends(current_user)) -> User:
        if u.role != role:
            raise HTTPException(403, f"{role} only")
        return u
    return dep