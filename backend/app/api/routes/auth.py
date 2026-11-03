from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import User, AuthSession, utcnow
from app.schemas.inputs import Login
from app.schemas.accounts import ProfileUpdate, PasswordUpdate
from app.api.routes.accounts import available_email
from app.security.auth import current_user, limit_login, password_matches, new_session, PERMISSIONS, hasher
from app.core.config import settings
from app.repositories.records import audit
from app.security.portfolio import portfolio_allowed

router = APIRouter(prefix="/auth", tags=["Sessão"])
dummy_hash = hasher.hash("dummy-non-user-password")


def user_info(user, csrf):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role,
        "permissions": sorted(PERMISSIONS.get(user.role, set())), "csrf_token": csrf}


@router.post("/login")
def login(data: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    limit_login(request.client.host if request.client else "unknown")
    user = db.scalar(select(User).where(User.email == str(data.email).lower(), User.active.is_(True)))
    verified = password_matches(user.password_hash if user else dummy_hash, data.password)
    if not user or not verified:
        raise HTTPException(401, "E-mail ou senha incorretos.")
    if user.role == "portfolio" and not portfolio_allowed(db, user):
        raise HTTPException(403, "Acesso de portfólio indisponível neste ambiente.")
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))
    token, csrf = new_session(db, user)
    audit(db, user, "login", "usuarios", user.id)
    db.commit()
    response.set_cookie("fitnota_session", token, httponly=True, secure=settings().cookie_secure,
        samesite="lax", max_age=settings().session_hours * 3600, path="/")
    return user_info(user, csrf)


@router.get("/portfolio")
def portfolio_credentials(db: Session = Depends(get_db)):
    cfg = settings()
    if not cfg.portfolio_enabled:
        return {"enabled": False}
    user = db.scalar(select(User).where(User.email == cfg.portfolio_email.lower(), User.role == "portfolio"))
    if not user or not portfolio_allowed(db, user) or not password_matches(user.password_hash, cfg.portfolio_password):
        return {"enabled": False}
    # Credenciais públicas da conta dedicada, habilitadas explicitamente para demonstração.
    return {"enabled": True, "email": cfg.portfolio_email, "password": cfg.portfolio_password}


@router.get("/me")
def me(request: Request, user=Depends(current_user)):
    return user_info(user, request.state.auth.csrf_token)


def verify_account_password(user, password, request):
    if user.role == "portfolio":
        raise HTTPException(403, "Os dados e a senha da conta pública não podem ser alterados.")
    limit_login(f"account:{user.id}:{request.client.host if request.client else 'unknown'}")
    if not password_matches(user.password_hash, password.get_secret_value()):
        raise HTTPException(400, "A senha atual está incorreta.")


def refresh_account_session(db, user, response):
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    token, csrf = new_session(db, user)
    db.commit()
    response.set_cookie("fitnota_session", token, httponly=True, secure=settings().cookie_secure,
        samesite="lax", max_age=settings().session_hours * 3600, path="/")
    return user_info(user, csrf)


@router.put("/me")
def update_me(data: ProfileUpdate, request: Request, response: Response,
        user=Depends(current_user), db: Session = Depends(get_db)):
    verify_account_password(user, data.current_password, request)
    available_email(db, str(data.email), user.id)
    user.name, user.email = data.name, str(data.email)
    audit(db, user, "atualizar_perfil", "usuarios", user.id)
    return refresh_account_session(db, user, response)


@router.put("/password")
def update_password(data: PasswordUpdate, request: Request, response: Response,
        user=Depends(current_user), db: Session = Depends(get_db)):
    verify_account_password(user, data.current_password, request)
    if password_matches(user.password_hash, data.new_password.get_secret_value()):
        raise HTTPException(400, "Escolha uma senha diferente da atual.")
    user.password_hash = hasher.hash(data.new_password.get_secret_value())
    audit(db, user, "alterar_senha", "usuarios", user.id, "Outras sessões encerradas.")
    return refresh_account_session(db, user, response)


@router.post("/logout")
def logout(request: Request, response: Response, user=Depends(current_user), db: Session = Depends(get_db)):
    db.delete(request.state.auth)
    audit(db, user, "logout", "usuarios", user.id)
    db.commit()
    response.delete_cookie("fitnota_session", path="/")
    return {"message": "Sessão encerrada"}
