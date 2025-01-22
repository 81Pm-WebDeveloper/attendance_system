from pydantic import BaseModel
from typing import Optional

class EmployeeBase(BaseModel):
    
    name: str
    department: str
    position: str

class EmployeeResponse(EmployeeBase):
    employee_id: int
    
    class Config:
        orm_mode = True