from pydantic import BaseModel
from typing import Optional

class EmployeeBase(BaseModel):
    employee_id: int
    name: str
    department: str
    position: str

class EmployeeResponse(EmployeeBase):
    employee_id: int
    
    class Config:
        from_attributes = True