from pydantic import BaseModel
from typing import Optional


class UpdateSummary(BaseModel):
    id: int
    status: str
    remarks: Optional[str] = None

    class Config:
        from_attributes = True

