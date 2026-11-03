"""Provisionamento explícito da conta pública de portfólio, separado do administrador."""
from sqlalchemy import select, delete
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.entities import Academy, FiscalConfig, User, AuthSession
from app.security.auth import hasher, password_matches


def provision():
    cfg = settings()
    if not cfg.portfolio_enabled:
        print("Acesso de portfólio desabilitado.")
        return
    if len(cfg.portfolio_password) < 12 or cfg.portfolio_email.lower() == cfg.demo_email.lower():
        raise SystemExit("Configure uma conta de portfólio própria com senha de pelo menos 12 caracteres.")
    with SessionLocal() as db:
        academy = db.scalar(select(Academy).join(FiscalConfig).where(FiscalConfig.environment == "demonstracao", FiscalConfig.provider == "simulador").order_by(Academy.id))
        if not academy:
            raise SystemExit("Aplique o seed demonstrativo antes de provisionar o portfólio.")
        user = db.scalar(select(User).where(User.email == cfg.portfolio_email.lower()))
        if user and (user.role != "portfolio" or user.academy_id != academy.id):
            raise SystemExit("E-mail de portfólio já pertence a outra conta. Configure outro e-mail.")
        if not user:
            user = User(academy_id=academy.id, name="Visitante • Portfólio", email=cfg.portfolio_email.lower(), role="portfolio", password_hash=hasher.hash(cfg.portfolio_password))
            db.add(user)
        elif not password_matches(user.password_hash, cfg.portfolio_password):
            user.password_hash = hasher.hash(cfg.portfolio_password)
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        user.active = True
        db.commit()
    print("Conta pública de portfólio preparada para demonstração.")


if __name__ == "__main__":
    provision()
