"""Casos de recrutamento: somente NFS-e simulada, banco e transportes fictícios.

Não chama prefeitura, SMTP, n8n, gateway ou provedores externos.
Os valores abaixo são cenários sintéticos, não emissão/receita real.
"""
from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.entities import Charge, FiscalEvent, Invoice, Payment
from conftest import login


def _fixture(client):
    person = client.post(
        "/api/clients",
        json={"name": "Empresa Demonstração Ltda", "person_type": "pj", "cnpj": "11222333000181"},
    )
    assert person.status_code == 201, person.text
    service = client.post(
        "/api/services", json={"name": "Consultoria de demonstração", "price": "350.00"}
    )
    assert service.status_code == 201, service.text
    return {
        "client_id": person.json()["id"],
        "service_id": service.json()["id"],
        "amount": "350.00",
        "competence": "2026-11",
        "description": "Serviço fictício para entrevista técnica",
    }


def test_case_preflight_issue_documents_and_no_financial_side_effects(authenticated):
    c = authenticated
    payload = _fixture(c)
    preview = c.post("/api/fiscal/preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert all(item["passed"] for item in preview.json()["checks"])
    assert preview.json()["environment"] == "demonstracao"
    key = "recrutamento-direct-20261108-key"
    emitted = c.post("/api/fiscal/issue-direct", json=payload, headers={"Idempotency-Key": key})
    assert emitted.status_code == 201, emitted.text
    body = emitted.json()
    assert body["status"] == "autorizada"
    assert body["origin"] == "avulsa" and body["charge_id"] is None
    assert body["identifier"].startswith("SIM-")

    html = c.get(f"/api/invoices/{body['id']}/document")
    assert html.status_code == 200
    assert "DOCUMENTO SIMULADO" in html.text
    assert "SEM VALIDADE FISCAL" in html.text

    pdf = c.get(f"/api/invoices/{body['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    xml = c.get(f"/api/invoices/{body['id']}/xml")
    assert xml.status_code == 200 and xml.content

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 1
        assert db.scalar(select(func.count()).select_from(Charge)) == 0
        assert db.scalar(select(func.count()).select_from(Payment)) == 0
        invoice = db.get(Invoice, body["id"])
        assert invoice.document_snapshot["environment"] == "demonstracao"
        assert invoice.identifier.startswith("SIM-")


def test_case_idempotency_rejection_retry_cancel_and_event_history(authenticated):
    c = authenticated
    payload = {**_fixture(c), "simulate_rejection": True}
    key = "recrutamento-retry-20261108-key"
    headers = {"Idempotency-Key": key}
    first = c.post("/api/fiscal/issue-direct", json=payload, headers=headers)
    assert first.status_code == 201 and first.json()["status"] == "rejeitada", first.text
    identity = first.json()["id"]

    replay = c.post("/api/fiscal/issue-direct", json=payload, headers=headers)
    assert replay.status_code == 201 and replay.json()["id"] == identity
    altered = c.post(
        "/api/fiscal/issue-direct",
        json={**payload, "amount": "351.00"},
        headers=headers,
    )
    assert altered.status_code == 409

    retried = c.post(f"/api/invoices/{identity}/retry")
    assert retried.status_code == 200 and retried.json()["status"] == "autorizada"
    assert c.post(f"/api/invoices/{identity}/retry").status_code == 409
    cancelled = c.post(
        f"/api/invoices/{identity}/cancel",
        json={"reason": "Cancelamento simulado para demonstração"},
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelada"
    assert c.post(
        f"/api/invoices/{identity}/cancel",
        json={"reason": "Tentativa repetida no cenário sintético"},
    ).status_code == 409

    detail = c.get(f"/api/invoices/{identity}")
    assert detail.status_code == 200
    statuses = [x["status"] for x in detail.json()["events"]]
    assert "rejeitada" in statuses
    assert "autorizada" in statuses
    assert "cancelamento_solicitado" in statuses
    assert statuses[-1] == "cancelada"
    cancelled_doc = c.get(f"/api/invoices/{identity}/document")
    assert cancelled_doc.status_code == 200
    assert "SEM VALIDADE FISCAL" in cancelled_doc.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 1
        assert db.scalar(select(func.count()).select_from(FiscalEvent)) == len(statuses)


def test_case_reception_cannot_issue_or_cancel_and_invalid_data_rejected(authenticated):
    c = authenticated
    payload = _fixture(c)
    assert c.post("/api/fiscal/preview", json={**payload, "amount": "0"}).status_code == 422
    assert c.post(
        "/api/fiscal/issue-direct",
        json={**payload, "competence": "2026-13"},
        headers={"Idempotency-Key": "recruiting-invalid-competence"},
    ).status_code == 422
    assert c.post(
        "/api/fiscal/issue-direct", json=payload, headers={"Idempotency-Key": "short"}
    ).status_code == 422

    emitted = c.post(
        "/api/fiscal/issue-direct",
        json=payload,
        headers={"Idempotency-Key": "recrutamento-role-20261108-key"},
    )
    assert emitted.status_code == 201
    identity = emitted.json()["id"]
    c.post("/api/auth/logout")
    login(c, "recepcao")
    assert c.post("/api/fiscal/preview", json=payload).status_code == 403
    assert c.post(
        "/api/fiscal/issue-direct",
        json=payload,
        headers={"Idempotency-Key": "recrutamento-role-denied-key"},
    ).status_code == 403
    assert c.post(
        f"/api/invoices/{identity}/cancel",
        json={"reason": "Recepção não pode cancelar este documento"},
    ).status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 1
        assert db.get(Invoice, identity).status == "autorizada"
