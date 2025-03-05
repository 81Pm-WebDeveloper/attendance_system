from pydantic import BaseModel,Field
from typing import Optional


class InsertSummary(BaseModel):
    employee_id: int
    issue_date: str
    expiry_date: str
    
    class Config:
        from_attributes = True

