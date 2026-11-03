from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str = "sqlite:///./fitnota.db"
    allowed_origins: str = "http://localhost:5180,http://127.0.0.1:5180,http://localhost:8080"
    cookie_secure: bool = False
    session_hours: int = 8
    demo_password: str = ""
    demo_admin_password: str = ""
    demo_email: str = "admin@nexofiscal.example.com"
    portfolio_enabled: bool = False
    portfolio_email: str = "portfolio@nexofiscal.example.com"
    portfolio_password: str = "NexoFiscalDemo@2026"
    automation_token: str = ""
    n8n_webhook_url: str = ""
    n8n_health_url: str = ""
    n8n_encryption_key: str = ""
    n8n_editor_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "NexoFiscal"


@lru_cache
def settings():
    return Settings()
