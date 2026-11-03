from sqlalchemy import select
from app.core.config import settings
from app.models.entities import FiscalConfig


def portfolio_allowed(db, user):
    cfg = settings()
    if not cfg.portfolio_enabled or user.role != "portfolio" or user.email != cfg.portfolio_email.lower() or not user.active:
        return False
    fiscal = db.scalar(select(FiscalConfig).where(FiscalConfig.academy_id == user.academy_id))
    return bool(fiscal and fiscal.environment == "demonstracao" and fiscal.provider == "simulador")
