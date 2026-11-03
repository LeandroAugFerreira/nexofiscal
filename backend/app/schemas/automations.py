from pydantic import Field
from app.schemas.inputs import Input


class AutomationExecution(Input):
    charge_id: int | None = Field(default=None, gt=0)
    invoice_id: int | None = Field(default=None, gt=0)
    competence: str | None = Field(default=None, pattern=r'^\d{4}-(0[1-9]|1[0-2])$')
    days: int = Field(default=7, ge=1, le=90)
