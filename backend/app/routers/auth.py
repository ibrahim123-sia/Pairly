from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.orm import Session

from app.config import get_config
from app.database import get_db
from app.dependencies import get_current_user, security
from app.models import Store, User, UserRole
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)
from app.services import auth_service
from app.services.audit_service import log_event
from app.services.email_service import send_password_reset_email

config = get_config()
router = APIRouter()


def create_access_token(user_id: int, role: str) -> str:
    expires = datetime.utcnow() + config.JWT_ACCESS_TOKEN_EXPIRES
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expires,
        "type": "access"
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int, role: str) -> str:
    expires = datetime.utcnow() + config.JWT_REFRESH_TOKEN_EXPIRES
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expires,
        "type": "refresh"
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")


@router.post("/login")
def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.lower().strip()
    password = payload.password
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password required"
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        log_event(db, "login_failed", metadata={"email": email, "reason": "user_not_found"}, request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    if not user.is_active:
        log_event(db, "login_failed", actor=user, metadata={"reason": "user_inactive"}, request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked"
        )

    if not auth_service.verify_password(password, user.password_hash):
        auth_service.register_failed_login(db, user)
        log_event(db, "login_failed", actor=user, metadata={"reason": "bad_password"}, request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if user.role == UserRole.STORE_MANAGER and user.store_id:
        store = db.get(Store, user.store_id)
        if store and not store.is_active:
            log_event(db, "login_failed", actor=user, metadata={"reason": "store_disabled"}, request=request)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your store has been disabled"
            )

    auth_service.register_successful_login(db, user)
    log_event(db, "login", actor=user, request=request)

    user_payload = user.to_dict()
    store_payload = None
    if user.store_id:
        store_obj = db.get(Store, user.store_id)
        if store_obj:
            store_payload = store_obj.to_dict()

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role)

    return {
        "user": user_payload,
        "store": store_payload,
        "access_token": access_token,
        "refresh_token": refresh_token
    }


@router.post("/refresh")
def refresh(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh")

    new_access_token = create_access_token(user.id, user.role)
    return {"access_token": new_access_token}


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    log_event(db, "logout", actor=current_user, request=request)
    return {"ok": True}


@router.get("/me")
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_payload = current_user.to_dict()
    store_payload = None
    if current_user.store_id:
        store_obj = db.get(Store, current_user.store_id)
        if store_obj:
            store_payload = store_obj.to_dict()
    return {"user": user_payload, "store": store_payload}


@router.post("/change-password")
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current = payload.current_password
    new = payload.new_password
    if len(new) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )
    if not auth_service.verify_password(current, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    current_user.password_hash = auth_service.hash_password(new)
    current_user.must_change_password = False
    db.commit()
    log_event(db, "password_changed", actor=current_user, request=request)
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.lower().strip()
    log_event(db, "password_reset_requested", metadata={"email": email}, request=request)
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user and user.is_active:
            ip = request.headers.get("X-Forwarded-For")
            if not ip and request.client:
                ip = request.client.host
            token = auth_service.create_password_reset_token(db, user, ip=ip)
            send_password_reset_email(user, token, db=db)
    return {"ok": True, "message": "If the account exists, a reset email has been sent."}


@router.post("/reset-password")
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    raw_token = payload.token
    new_password = payload.new_password
    if not raw_token or len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token or password"
        )
    token = auth_service.consume_password_reset_token(db, raw_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is invalid or expired"
        )
    user = db.get(User, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account not available"
        )
    user.password_hash = auth_service.hash_password(new_password)
    user.must_change_password = False
    auth_service.mark_token_used(db, token)
    log_event(db, "password_reset_completed", actor=user, request=request)
    return {"ok": True}
