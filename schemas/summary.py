from pydantic import BaseModel,Field
from typing import Optional


class UpdateSummary(BaseModel):
    id: int
    status: str
    remarks: Optional[str] = None
    checkout_status: Optional[str] = None

    class Config:
        from_attributes = True

