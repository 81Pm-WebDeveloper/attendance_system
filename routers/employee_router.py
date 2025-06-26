from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.employee_service as employeeService
from db.database import get_db
from schemas.employees import EmployeeBase
from config.authentication import verify_key
router = APIRouter()

#DISREGARD THIS PAGE
@router.post("/",status_code=201, dependencies=[Depends(verify_key)])
def insert_employee(employee: EmployeeBase, db: Session = Depends(get_db)):
    try:
        result = employeeService.insert_employee(db=db, employee=employee)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")