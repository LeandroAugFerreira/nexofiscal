from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, JSON, Date, DateTime, Boolean, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Record:
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Academy(Record, Base):
    __tablename__ = "academias"
    legal_name: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(120))
    cnpj: Mapped[str] = mapped_column(String(14), unique=True)
    municipal_registration: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    address: Mapped[dict] = mapped_column(JSON, default=dict)
    tax_regime: Mapped[str] = mapped_column(String(100), default="Não configurado")


class FiscalConfig(Record, Base):
    __tablename__ = "configuracoes_fiscais"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), unique=True)
    environment: Mapped[str] = mapped_column(String(30), default="demonstracao")
    provider: Mapped[str] = mapped_column(String(50), default="simulador")
    municipality: Mapped[str] = mapped_column(String(120), default="")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)


class User(Record, Base):
    __tablename__ = "usuarios"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30), default="recepcao")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthSession(Record, Base):
    __tablename__ = "sessoes"
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Student(Record, Base):
    __tablename__ = "alunos"
    __table_args__ = (UniqueConstraint("academy_id", "cpf"), UniqueConstraint("academy_id","cnpj",name="uq_clientes_cnpj"),
        CheckConstraint("(person_type = 'pf' AND cpf IS NOT NULL AND cnpj IS NULL) OR (person_type = 'pj' AND cnpj IS NOT NULL AND cpf IS NULL)",name="ck_clientes_documento"))
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    person_type: Mapped[str] = mapped_column(String(2),default="pf",server_default="pf")
    cpf: Mapped[str | None] = mapped_column(String(11))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    trade_name: Mapped[str] = mapped_column(String(120),default="",server_default="")
    municipal_registration: Mapped[str] = mapped_column(String(50),default="",server_default="")
    birth_date: Mapped[date | None] = mapped_column(Date)
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    address: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="ativo", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class Plan(Record, Base):
    __tablename__ = "planos"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    period_months: Mapped[int] = mapped_column(default=1)
    services: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="ativo")
    __table_args__ = (CheckConstraint("price >= 0"), CheckConstraint("period_months > 0"))


class Service(Record, Base):
    __tablename__ = "servicos"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(30), default="sessão")
    status: Mapped[str] = mapped_column(String(30), default="ativo")
    fiscal_reference: Mapped[str] = mapped_column(String(200), default="Não configurada")
    __table_args__ = (CheckConstraint("price >= 0"),)


class Contract(Record, Base):
    __tablename__ = "contratos"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("planos.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    due_day: Mapped[int] = mapped_column(default=10)
    status: Mapped[str] = mapped_column(String(30), default="ativo")
    __table_args__ = (CheckConstraint("amount >= 0"), CheckConstraint("due_day BETWEEN 1 AND 28"),)


class Charge(Record, Base):
    __tablename__ = "cobrancas"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contratos.id"), index=True)
    competence: Mapped[str] = mapped_column(String(7))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    surcharge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(30), default="pendente", index=True)
    __table_args__ = (UniqueConstraint("contract_id", "competence"), CheckConstraint("amount >= 0"), CheckConstraint("paid >= 0 AND paid <= amount"))


class Payment(Record, Base):
    __tablename__ = "pagamentos"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    charge_id: Mapped[int] = mapped_column(ForeignKey("cobrancas.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_at: Mapped[date] = mapped_column(Date)
    method: Mapped[str] = mapped_column(String(40))
    reference: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(30), default="registrado_manual")
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    __table_args__ = (CheckConstraint("amount > 0"),)


class Invoice(Record, Base):
    __tablename__ = "notas_fiscais"
    __table_args__ = (CheckConstraint("(origin = 'cobranca' AND charge_id IS NOT NULL) OR (origin = 'avulsa' AND charge_id IS NULL AND service_id IS NOT NULL)", name="ck_notas_origem"),)
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    charge_id: Mapped[int | None] = mapped_column(ForeignKey("cobrancas.id"), unique=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("servicos.id", name="fk_notas_servico"))
    origin: Mapped[str] = mapped_column(String(20), default="cobranca", server_default="cobranca")
    competence: Mapped[str | None] = mapped_column(String(7))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    student_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    service_description: Mapped[str] = mapped_column(Text)
    identifier: Mapped[str | None] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="aguardando_emissao", index=True)
    environment: Mapped[str] = mapped_column(String(30), default="demonstracao")
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    document: Mapped[str | None] = mapped_column(Text)
    document_snapshot: Mapped[dict | None] = mapped_column(JSON)
    document_pdf: Mapped[bytes | None] = mapped_column(LargeBinary)
    document_xml: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(default=0)


class FiscalEvent(Record, Base):
    __tablename__ = "eventos_fiscais"
    invoice_id: Mapped[int] = mapped_column(ForeignKey("notas_fiscais.id"), index=True)
    status: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)


class EmailDelivery(Record, Base):
    __tablename__ = "entregas_email"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"),index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("notas_fiscais.id"),index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30),default="preparando")
    idempotency_key: Mapped[str] = mapped_column(String(100),unique=True)
    message: Mapped[str] = mapped_column(Text,default="")


class FiscalBatch(Record, Base):
    __tablename__ = "lotes_fiscais"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"))
    status: Mapped[str] = mapped_column(String(30), default="rascunho")


class BatchItem(Record, Base):
    __tablename__ = "itens_lote_fiscal"
    batch_id: Mapped[int] = mapped_column(ForeignKey("lotes_fiscais.id"))
    charge_id: Mapped[int] = mapped_column(ForeignKey("cobrancas.id"))
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("batch_id", "charge_id"),)


class Automation(Record, Base):
    __tablename__ = "automacoes"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"))
    name: Mapped[str] = mapped_column(String(150))
    workflow_key: Mapped[str] = mapped_column(String(80), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    implemented: Mapped[bool] = mapped_column(Boolean, default=False)


class AutomationRun(Record, Base):
    __tablename__ = "execucoes_automacoes"
    automation_id: Mapped[int] = mapped_column(ForeignKey("automacoes.id"), index=True)
    charge_id: Mapped[int | None] = mapped_column(ForeignKey("cobrancas.id"))
    status: Mapped[str] = mapped_column(String(30), default="pendente")
    message: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="n8n", server_default="n8n")
    result_data: Mapped[dict | None] = mapped_column(JSON)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    request_hash: Mapped[str | None] = mapped_column(String(64))


class Audit(Record, Base):
    __tablename__ = "auditoria"
    academy_id: Mapped[int] = mapped_column(ForeignKey("academias.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int | None]
    result: Mapped[str] = mapped_column(String(30), default="sucesso")
    details: Mapped[str] = mapped_column(Text, default="")
