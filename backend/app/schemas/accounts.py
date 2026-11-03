from typing import Literal
from pydantic import ConfigDict, EmailStr, Field, SecretStr, field_validator
from app.schemas.inputs import Input


Role = Literal["administrador", "financeiro", "recepcao", "contabilidade"]


class AccountInput(Input):
    model_config = ConfigDict(str_strip_whitespace=False)


class AccountData(AccountInput):
    name: str = Field(min_length=3, max_length=120)
    email: EmailStr = Field(max_length=200)

    @field_validator("name", "email", mode="before")
    @classmethod
    def trim_identity(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class UserCreate(AccountData):
    role: Role = "recepcao"
    active: bool = True
    password: SecretStr = Field(min_length=8, max_length=128)


class UserUpdate(AccountData):
    role: Role
    active: bool
    password: SecretStr | None = Field(default=None, min_length=8, max_length=128)


class ProfileUpdate(AccountData):
    current_password: SecretStr = Field(min_length=1, max_length=128)


class PasswordUpdate(AccountInput):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)
