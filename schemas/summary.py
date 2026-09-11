from datetime import date as Date
from pydantic import BaseModel,Field
from typing import Optional


class UpdateSummary(BaseModel):
    status: str
    id: Optional[int] = None
    employee_id: Optional[int] = None
    date: Optional[Date] = None
    remarks: Optional[str] = None
    checkout_status: Optional[str] = None

    class Config:
        from_attributes = True

