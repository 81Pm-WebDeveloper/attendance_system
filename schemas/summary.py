from pydantic import BaseModel,Field
from typing import Optional


class UpdateSummary(BaseModel):
    id: int
    status: str
    remarks: Optional[str] 
    checkout_status: Optional[str]

    class Config:
        from_attributes = True

