import hashlib
import secrets
import string
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy.orm import Session

from app.models import PasswordResetToken, User, UserRole
from config import get_config

config = get_config()


def hash_password(plain: str) -> str:
    pwd_bytes = plain.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
        ):
            return pwd


def ensure_super_admin(db: Session):
    email = config.SUPER_ADMIN_EMAIL.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if existing.role != UserRole.SUPER_ADMIN:
            existing.role = UserRole.SUPER_ADMIN
            db.commit()
        return existing
    admin = User(
        email=email,
        password_hash=hash_password(config.SUPER_ADMIN_PASSWORD),
        role=UserRole.SUPER_ADMIN,
        full_name=config.SUPER_ADMIN_NAME,
        is_email_verified=True,
        is_active=True,
        must_change_password=False,
    )
    db.add(admin)
    db.commit()
    return admin


def register_failed_login(db: Session, user: User):
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= config.LOGIN_LOCKOUT_THRESHOLD:
        user.locked_until = datetime.utcnow() + timedelta(minutes=config.LOGIN_LOCKOUT_MINUTES)
        user.failed_login_count = 0
    db.commit()


def register_successful_login(db: Session, user: User):
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    db.commit()


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, user: User, ip=None):
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None)
    ).delete()
    raw = secrets.token_urlsafe(48)
    ttl = config.PASSWORD_RESET_TTL_MINUTES
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=_token_hash(raw),
        expires_at=datetime.utcnow() + timedelta(minutes=ttl),
        created_ip=ip,
    )
    db.add(token)
    db.commit()
    return raw


def consume_password_reset_token(db: Session, raw_token: str):
    token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == _token_hash(raw_token)
    ).first()
    if not token or not token.is_valid:
        return None
    return token


def mark_token_used(db: Session, token: PasswordResetToken):
    token.used_at = datetime.utcnow()
    db.commit()
