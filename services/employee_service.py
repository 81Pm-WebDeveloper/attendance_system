from fastapi import HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.attendance import Attendance
from models.employees import Employee
from datetime import datetime, date
from sqlalchemy import asc, or_,desc
from zk import ZK
from sqlalchemy.sql import func
from schemas.employees import EmployeeBase

def insert_employee(db: Session, employee: EmployeeBase):
    new_employee = Employee(**employee.model_dump())
    
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)  
    
    return new_employee

