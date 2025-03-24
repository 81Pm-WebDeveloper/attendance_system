from pydantic import BaseModel
from typing import Optional,List


class AttendanceBase(BaseModel):
    employee_id: str
    date: str
    time_in: Optional[str]
    time_out: Optional[str]
    status: Optional[str]

class AttendanceResponse(AttendanceBase):
    id: int

    class Config:
        from_attributes = True

class AttendanceToday(BaseModel):
    employee_id: int
    name: str
    department: str
    position: str
    status: str

class CheckVoucher(BaseModel):
    employee_id: int
    date: str

class VoucherUseRequest(BaseModel):
    voucher_id: int
    att_id: int

class Parso(BaseModel):
    employee_id: int
    date: str
    vouchers: List[int]
    
