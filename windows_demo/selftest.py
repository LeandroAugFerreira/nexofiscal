import json
import sqlite3
import sys
from datetime import date


def run(url, folder, bundle, make_window):
    import httpx
    from app.core.config import settings
    from app.database.session import SessionLocal
    from app.models.entities import Student, Service, User
    from sqlalchemy import select, func
    assert not any((settings().smtp_host, settings().smtp_password, settings().n8n_webhook_url, settings().automation_token))
    root = make_window(url, folder, hidden=True); root.update_idletasks(); root.update(); root.destroy()
    with httpx.Client(base_url=url, headers={"Origin": url}, timeout=25) as client:
        for path in ("/login", "/fiscal"):
            response = client.get(path); assert response.status_code == 200 and '<div id="root">' in response.text
        assert client.get("/api/missing-route").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api/health").json()["fiscal"] == "simulador"
        assert client.get("/api/clients").status_code == 401
        credentials = client.get("/api/auth/portfolio").json(); assert credentials["enabled"]
        response = client.post("/api/auth/login", json={key: credentials[key] for key in ("email", "password")})
        assert response.status_code == 200, response.text
        account = response.json(); assert account["role"] == "portfolio"
        client.headers["X-CSRF-Token"] = account["csrf_token"]
        assert client.get("/api/clients").status_code == 200
        with SessionLocal() as db:
            person = db.scalar(select(Student).where(Student.status == "ativo").order_by(Student.id))
            service = db.scalar(select(Service).where(Service.status == "ativo").order_by(Service.id))
            data = {"client_id": person.id, "service_id": service.id, "amount": "350.00", "competence": date.today().strftime("%Y-%m"), "description": "Teste isolado da demonstração Windows"}
        response = client.post("/api/fiscal/preview", json=data); assert response.status_code == 200, response.text
        assert "SEM VALIDADE FISCAL" in response.json()["message"]
        response = client.post("/api/fiscal/issue-direct", headers={"Idempotency-Key": "desktop-selftest-20261101"}, json=data)
        assert response.status_code == 201, response.text
        invoice = response.json(); assert invoice["identifier"].startswith("SIM-")
        pdf = client.get(f"/api/invoices/{invoice['id']}/pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
        assert "SEM VALIDADE FISCAL" in client.get(f"/api/invoices/{invoice['id']}/document").text
        draft = client.post(f"/api/invoices/{invoice['id']}/email-draft", json={"recipient": "cliente@nexofiscal.example.com"})
        assert draft.status_code == 200
        blocked = client.post(f"/api/invoices/{invoice['id']}/email-send", headers={"Idempotency-Key": "desktop-no-mail-20261101"}, json={"recipient": "cliente@nexofiscal.example.com"})
        assert blocked.status_code == 403
        assert client.post("/api/auth/logout").status_code == 200
    from app.seed import seed
    from app.portfolio import provision
    with SessionLocal() as db: before = db.scalar(select(func.count(User.id)))
    seed(); provision()
    with SessionLocal() as db: assert db.scalar(select(func.count(User.id))) == before
    with sqlite3.connect(folder / "nexofiscal-demo.db") as db:
        assert db.execute("pragma integrity_check").fetchone()[0] == "ok"
        assert db.execute("pragma foreign_key_check").fetchall() == []
    (folder / "self-test.json").write_text(json.dumps({"product": "NexoFiscal 0.1.0", "frozen": bool(getattr(sys, "frozen", False)),
        "frontend_spa": True, "authentication_csrf": True, "portfolio_account": True, "fiscal_simulation": True, "pdf_generated": True,
        "email_draft": True, "real_email_blocked": True, "smtp_configured": False, "n8n_configured": False, "seed_idempotent": True,
        "database_integrity": "ok", "tk_initialized": True}, indent=2), encoding="utf-8")
