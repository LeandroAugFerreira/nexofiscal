import hashlib
import secrets
from datetime import timedelta
from collections import defaultdict, deque
from time import monotonic
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import AuthSession, User, utcnow
from app.core.config import settings
from app.security.portfolio import portfolio_allowed

hasher = PasswordHasher()
attempts = defaultdict(deque)
PERMISSIONS = {
    "administrador": {"read", "students", "catalog", "finance", "fiscal", "cancel", "settings", "audit", "users", "automation", "email_send"},
    "financeiro": {"read", "students", "catalog", "finance", "fiscal", "automation", "email_send"},
    "recepcao": {"read", "students"},
    "contabilidade": {"read", "fiscal", "audit"},
}
PERMISSIONS["portfolio"] = PERMISSIONS["administrador"].copy()
PERMISSIONS["portfolio"].discard("email_send")


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def password_matches(hash_value, password):
    try:
        return hasher.verify(hash_value, password)
    except (VerificationError, InvalidHashError):
        return False


def limit_login(key):
    now = monotonic()
    queue = attempts[key]
    while queue and now - queue[0] > 300:
        queue.popleft()
    if len(queue) >= 10:
        raise HTTPException(429, "Muitas tentativas. Aguarde cinco minutos.")
    queue.append(now)


def new_session(db, user):
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db.add(AuthSession(user_id=user.id, token_hash=token_hash(token), csrf_token=csrf,
        expires_at=utcnow() + timedelta(hours=settings().session_hours)))
    return token, csrf


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("fitnota_session")
    auth = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token or ""), AuthSession.expires_at > utcnow()))
    user = db.get(User, auth.user_id) if auth else None
    if not user or not user.active:
        raise HTTPException(401, "Sua sessão expirou. Entre novamente.")
    if user.role == "portfolio" and not portfolio_allowed(db, user):
        raise HTTPException(401, "O acesso de portfólio foi desabilitado.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(csrf, auth.csrf_token):
            raise HTTPException(403, "Sessão inválida. Atualize a página.")
    request.state.auth = auth
    return user


def require(permission):
    def dependency(user: User = Depends(current_user)):
        if permission not in PERMISSIONS.get(user.role, set()):
            raise HTTPException(403, "Seu perfil não permite esta operação.")
        return user
    return dependency
