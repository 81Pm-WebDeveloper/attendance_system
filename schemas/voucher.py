from pydantic import BaseModel,Field
from typing import Optional


class InsertVoucher(BaseModel):
    employee_id: int
    issue_date: str
    expiry_date: str
    
    class Config:
        from_attributes = True

class parsoVouchers(BaseModel):
    voucher_ids: list[int]
    date: str


class VoucherUpdateItem(BaseModel):
    attendance_id: int
    voucher_id: int

class VoucherUpdateRequest(BaseModel):
    updates: list[VoucherUpdateItem]