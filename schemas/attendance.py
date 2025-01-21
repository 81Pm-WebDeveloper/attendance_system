from pydantic import BaseModel
from typing import Optional


class AttendanceBase(BaseModel):
    employee_id: str
    date: str
    time_in: Optional[str]
    time_out: Optional[str]
    status: Optional[str]

class AttendanceResponse(AttendanceBase):
    id: int

    class Config:
        orm_mode = True