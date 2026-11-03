"""Confere a API e prepara uma mensagem fictícia. Não chama o endpoint de envio."""
import json
import os
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")


def main():
    import httpx
    from sqlalchemy import select, func
    from app.core.config import settings
    from app.database.session import SessionLocal
    from app.models.entities import Invoice, Student, User, EmailDelivery
    from app.security.auth import PERMISSIONS
    cfg = settings()
    report = {"email_sent": False, "configuration_modified": False, "roles": {}}
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == cfg.demo_email, User.active.is_(True)))
        if not user:
            raise RuntimeError("Administrador local configurado não encontrado.")
        company_id = user.academy_id
        invoice = db.scalar(select(Invoice).join(Student, Student.id == Invoice.student_id).where(
            Invoice.academy_id == company_id, Invoice.environment == "demonstracao", Invoice.status == "autorizada",
            Invoice.document_pdf.is_not(None), Student.notes.ilike("%fictício%"))
            .order_by(Invoice.id.desc()).limit(1))
        if not invoice:
            raise RuntimeError("Não há nota autorizada com PDF e cliente fictício para preparar o teste.")
        invoice_id, identifier = invoice.id, invoice.identifier
        rows = db.scalars(select(User).where(User.academy_id == company_id,
            User.active.is_(True), User.role.in_(["administrador", "financeiro"]))).all()
        role_users = {role: next((x for x in rows if x.role == role), None) for role in ("administrador", "financeiro")}
        before = db.scalar(select(func.count()).select_from(EmailDelivery))
    with httpx.Client(base_url="http://127.0.0.1:8010/api", timeout=15, trust_env=False) as client:
        health = client.get("/health"); health.raise_for_status()
        report["health_http"] = health.status_code
        schema = client.get("http://127.0.0.1:8010/openapi.json"); schema.raise_for_status()
        report["api_name"] = schema.json().get("info", {}).get("title")
        paths = schema.json().get("paths", {})
        report["email_routes"] = {"draft": "/api/invoices/{identity}/email-draft" in paths,
            "send": "/api/invoices/{identity}/email-send" in paths, "history": "/api/invoices/{identity}/email" in paths}
        for role, account in role_users.items():
            report["roles"][role] = {"active_user": bool(account), "permission": "email_send" in PERMISSIONS[role]}
            if account is None:
                continue
            login = client.post("/auth/login", json={"email": account.email, "password": cfg.demo_password})
            report["roles"][role]["login_http"] = login.status_code
            if login.status_code != 200:
                continue
            auth = login.json()
            report["roles"][role]["api_permission"] = "email_send" in auth["permissions"]
            headers = {"X-CSRF-Token": auth["csrf_token"]}
            config = client.get("/email/configuration"); config.raise_for_status()
            report["api_smtp_configured"] = config.json()["configured"]
            report["sender"] = config.json()["sender"]
            report["sender_matches_local"] = config.json()["sender"] == cfg.smtp_from_email
            if role == "administrador":
                draft = client.post(f"/invoices/{invoice_id}/email-draft", json={"recipient": cfg.smtp_from_email}, headers=headers)
                draft.raise_for_status()
                message = BytesParser(policy=policy.default).parsebytes(draft.content)
                attachments = list(message.iter_attachments())
                assert "[DEMONSTRAÇÃO]" in message["Subject"]
                assert "SEM VALIDADE FISCAL" in message.get_body(preferencelist=("plain",)).get_content()
                assert len(attachments) == 1 and attachments[0].get_payload(decode=True).startswith(b"%PDF-")
                output = ROOT / "output" / "email" / "nexofiscal-primeiro-teste.eml"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(draft.content)
                report["draft"] = {"invoice_id": invoice_id, "identifier": identifier,
                    "url": f"http://127.0.0.1:5180/invoices/{invoice_id}", "recipient": cfg.smtp_from_email,
                    "pdf_attached": True, "simulation_notice": True, "file": str(output)}
            client.post("/auth/logout", headers=headers)
            client.cookies.clear()
    with SessionLocal() as db:
        report["deliveries_unchanged"] = before == db.scalar(select(func.count()).select_from(EmailDelivery))
    output = ROOT / "artifacts" / "primeiro-teste-email.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if "draft" in report else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Respostas, tokens, cookies e credenciais não entram no diagnóstico.
        print(json.dumps({"error_type": type(error).__name__, "message": "A verificação não foi concluída; nenhuma mensagem foi enviada."}))
        raise SystemExit(1)
