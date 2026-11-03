from datetime import date
from decimal import Decimal
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, EmailStr, AliasChoices, field_validator, model_validator, StringConstraints
from app.utils.validation import digits, valid_cpf, valid_cnpj

Money = Decimal


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Address(Input):
    cep: str = Field(default="", max_length=9)
    street: str = Field(default="", max_length=160)
    number: str = Field(default="", max_length=20)
    complement: str = Field(default="", max_length=120)
    neighborhood: str = Field(default="", max_length=100)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=2)


class Login(Input):
    email: EmailStr
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=128)


class StudentInput(Input):
    name: str = Field(min_length=3, max_length=160)
    person_type: Literal["pf","pj"] = "pf"
    cpf: str | None = None
    cnpj: str | None = None
    trade_name: str = Field(default="",max_length=120)
    municipal_registration: str = Field(default="",max_length=50)
    birth_date: date | None = None
    email: EmailStr | Literal[""] = ""
    phone: str = Field(default="", max_length=30)
    address: Address = Field(default_factory=Address)
    status: Literal["ativo", "inativo"] = "ativo"
    notes: str = Field(default="", max_length=3000)

    @field_validator("cpf")
    @classmethod
    def cpf_check(cls, value):
        if not value:
            return None
        if not valid_cpf(value):
            raise ValueError("CPF inválido")
        return digits(value)

    @field_validator("cnpj")
    @classmethod
    def cnpj_check(cls,value):
        if not value:
            return None
        if not valid_cnpj(value):
            raise ValueError("CNPJ inválido")
        return digits(value)

    @model_validator(mode="after")
    def person_document(self):
        if self.person_type=="pf" and (not self.cpf or self.cnpj):
            raise ValueError("Pessoa física exige CPF; CNPJ deve ficar vazio")
        if self.person_type=="pj" and (not self.cnpj or self.cpf):
            raise ValueError("Pessoa jurídica exige CNPJ; CPF deve ficar vazio")
        if self.person_type=="pj" and self.birth_date:
            raise ValueError("Data de nascimento é exclusiva de pessoa física")
        return self

    @field_validator("birth_date")
    @classmethod
    def birth_check(cls, value):
        if value and value > date.today():
            raise ValueError("Nascimento não pode estar no futuro")
        return value


class PlanInput(Input):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=3000)
    price: Money = Field(ge=0, max_digits=12, decimal_places=2)
    period_months: int = Field(default=1, ge=1, le=36)
    services: str = Field(default="", max_length=3000)
    status: Literal["ativo", "inativo"] = "ativo"


class ServiceInput(Input):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=3000)
    price: Money = Field(ge=0, max_digits=12, decimal_places=2)
    unit: str = Field(default="sessão", min_length=1, max_length=30)
    status: Literal["ativo", "inativo"] = "ativo"
    fiscal_reference: str = Field(default="Não configurada", max_length=200)


class ContractInput(Input):
    student_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    amount: Money | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    start_date: date
    end_date: date | None = None
    due_day: int = Field(default=10, ge=1, le=28)

    @model_validator(mode="after")
    def dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Término anterior ao início")
        return self


class ContractStatus(Input):
    status: Literal["ativo", "suspenso", "cancelado"]


class ChargeInput(Input):
    contract_id: int = Field(gt=0)
    competence: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    due_date: date
    discount: Money = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    surcharge: Money = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class PaymentInput(Input):
    charge_id: int = Field(gt=0)
    amount: Money = Field(gt=0, max_digits=12, decimal_places=2)
    paid_at: date
    method: Literal["pix", "dinheiro", "credito", "debito", "boleto", "transferencia"]
    reference: str = Field(default="", max_length=200)


class InvoiceInput(Input):
    charge_id: int = Field(gt=0)
    simulate_rejection: bool = False


class DirectInvoiceInput(Input):
    student_id: int = Field(gt=0,validation_alias=AliasChoices("client_id","student_id"))
    service_id: int = Field(gt=0)
    amount: Money = Field(gt=0, max_digits=12, decimal_places=2)
    competence: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    description: str = Field(default="", max_length=2000)
    simulate_rejection: bool = False


class CancelInput(Input):
    reason: str = Field(min_length=10, max_length=1000)


class AcademyInput(Input):
    legal_name: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=3, max_length=120)
    cnpj: str
    municipal_registration: str = Field(default="", max_length=50)
    email: EmailStr | Literal[""] = ""
    phone: str = Field(default="", max_length=30)
    address: Address = Field(default_factory=Address)
    tax_regime: str = Field(default="Não configurado", max_length=100)

    @field_validator("cnpj")
    @classmethod
    def cnpj_check(cls, value):
        if not valid_cnpj(value):
            raise ValueError("CNPJ inválido")
        return digits(value)


class FiscalConfigInput(Input):
    environment: Literal["demonstracao"] = "demonstracao"
    provider: Literal["simulador"] = "simulador"
    municipality: str = Field(default="", max_length=120)


class AutomationToggle(Input):
    enabled: bool


class EmailDraftInput(Input):
    recipient: EmailStr | Literal[""] = ""


class EmailSendInput(Input):
    recipient: EmailStr
