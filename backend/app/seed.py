"""Seed fictício, explícito e idempotente. Nunca é executado automaticamente pela API."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select
from app.database.session import SessionLocal
from app.core.config import settings
from app.models.entities import (Academy, FiscalConfig, User, Student, Plan, Service, Contract,
    Charge, Payment, Invoice, Automation)
from app.security.auth import hasher
from app.schemas.inputs import InvoiceInput
from app.services.fiscal import issue, event, adapter


def fake_cpf(index):
    n = f"{900000000 + index:09d}"
    for length in (9, 10):
        check = (sum(int(n[i]) * (length + 1-i) for i in range(length))*10) % 11
        n += str(0 if check == 10 else check)
    return n


def seed():
    cfg = settings()
    password = cfg.demo_password
    if len(password) < 12:
        raise SystemExit("Defina DEMO_PASSWORD com ao menos 12 caracteres no .env ou ambiente.")
    admin_password = cfg.demo_admin_password or password
    if len(admin_password) < 8:
        raise SystemExit("Defina DEMO_ADMIN_PASSWORD com ao menos 8 caracteres.")
    with SessionLocal() as db:
        if db.scalar(select(Academy)):
            print("Seed já aplicado. Nenhum dado foi sobrescrito.")
            return
        academy = Academy(name="Horizonte Serviços • Demonstração", legal_name="Horizonte Serviços Ltda. (fictícia)",
            cnpj="00000000000191", email="contato@nexofiscal.example.com", phone="(11) 0000-0000",
            address={"city": "São Paulo", "state": "SP", "street": "Rua Exemplo", "number": "100", "cep": "01000-000"})
        db.add(academy)
        db.flush()
        db.add(FiscalConfig(academy_id=academy.id, municipality="São Paulo"))
        users = []
        for role, name, email in (("administrador", "Alex • Administrador", cfg.demo_email),
            ("financeiro", "Financeiro Demo", "financeiro@nexofiscal.example.com"),
            ("recepcao", "Recepção Demo", "recepcao@nexofiscal.example.com"),
            ("contabilidade", "Contabilidade Demo", "contabilidade@nexofiscal.example.com")):
            user = User(academy_id=academy.id, role=role, name=name, email=email.lower(),
                password_hash=hasher.hash(admin_password if role == "administrador" else password))
            db.add(user)
            users.append(user)
        plans = []
        for name, amount, period in (("Mensal", "119.90", 1), ("Profissional", "159.90", 1),
            ("Premium", "229.90", 1), ("Trimestral", "329.90", 3), ("Semestral", "599.90", 6), ("Anual", "1099.90", 12)):
            plan = Plan(academy_id=academy.id, name=name, price=Decimal(amount), period_months=period,
                description=f"Plano {name} • dados fictícios", services="Pacote de serviços contratado")
            db.add(plan)
            plans.append(plan)
        for name, price in (("Consultoria", "350"), ("Prestação de serviços", "180"), ("Suporte técnico", "120"),
            ("Treinamento", "250"), ("Desenvolvimento de projeto", "900")):
            db.add(Service(academy_id=academy.id, name=name, price=Decimal(price), description="Serviço fictício para demonstração do emissor"))
        db.flush()
        names = ["Ana Oliveira", "Bruno Santos", "Camila Costa", "Diego Almeida", "Elisa Rocha", "Felipe Lima",
            "Gabriela Souza", "Hugo Ferreira", "Isabela Martins", "João Silva", "Karina Alves", "Lucas Ribeiro",
            "Mariana Pereira", "Nicolas Gomes", "Olívia Barbosa", "Pedro Carvalho", "Rafaela Dias", "Samuel Mendes",
            "Talita Ramos", "Vinícius Teixeira", "Beatriz Castro", "André Moreira", "Laura Azevedo", "Mateus Cardoso"]
        today = date.today()
        for index, name in enumerate(names):
            joined_month = max(1, today.month - index % 5)
            student = Student(academy_id=academy.id, name=name, cpf=fake_cpf(index+1),
                email=f"cliente{index+1}@nexofiscal.example.com", phone="(11) 90000-0000",
                birth_date=date(1990+index%12, 1+index%12, 10), address={"city": "São Paulo", "state": "SP"},
                notes="Cadastro fictício para demonstração.", created_at=datetime(today.year, joined_month, 1),
                status="inativo" if index == 23 else "ativo")
            db.add(student)
            db.flush()
            plan = plans[index % 3]
            contract = Contract(academy_id=academy.id, student_id=student.id, plan_id=plan.id,
                amount=plan.price, start_date=date(today.year, 1, 1), due_day=10)
            db.add(contract)
            db.flush()
            for offset in range(5):
                serial = today.year*12 + today.month-1-offset
                year, month = serial//12, serial%12+1
                due = date(year, month, 10 if index%2 == 0 else 20)
                charge = Charge(academy_id=academy.id, student_id=student.id, contract_id=contract.id,
                    competence=f"{year}-{month:02d}", due_date=due, original_amount=plan.price, amount=plan.price)
                db.add(charge)
                db.flush()
                if offset > 0 or index < 16:
                    charge.paid, charge.status = charge.amount, "paga"
                    db.add(Payment(academy_id=academy.id, charge_id=charge.id, amount=charge.amount,
                        paid_at=min(due, today), method=["pix", "credito", "dinheiro", "debito"][index%4],
                        reference="Seed fictício", idempotency_key=f"seed-payment-{charge.id}"))
                    if offset == 0 and index < 14:
                        invoice = issue(db, InvoiceInput(charge_id=charge.id, simulate_rejection=index == 12), users[0], f"seed-invoice-{charge.id}")
                        if index == 13:
                            adapter.cancelar_nota(invoice, "Cancelamento demonstrativo")
                            event(db, invoice, "cancelada", "Cancelamento demonstrativo")
        for key, name in (("payment-confirmed", "Pagamento registrado → emissão simulada"),
            ("document-delivery", "Entrega de documento"), ("due-reminders", "Avisos de vencimento"),
            ("failure-recovery", "Tratamento de falhas"), ("monthly-closing", "Fechamento mensal"), ("alerts", "Alertas operacionais")):
            db.add(Automation(academy_id=academy.id, workflow_key=key, name=name, implemented=True))
        db.commit()
        print(f"Demonstração criada: {cfg.demo_email}. Senha definida por DEMO_PASSWORD. Dados fictícios, sem validade fiscal.")


if __name__ == "__main__":
    seed()
    from app.general_demo import provision as general_demo
    general_demo()
    from app.portfolio import provision
    provision()
