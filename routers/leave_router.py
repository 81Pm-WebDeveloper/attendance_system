from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.leave_service as leaveService
from db.database2 import get_db2
from db.database import get_db

from schemas.attendance import Parso
from config.authentication import verify_key

router = APIRouter()
@router.post("/reward/",status_code=201,dependencies=[Depends(verify_key)])
def Parso(body: Parso,db:Session= Depends(get_db2)):
    """
    FOR PARSO APPLICATION
    """
    try:
        result = leaveService.reward_leave(db,body)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")
    
@router.get("/",status_code=200, dependencies=[Depends(verify_key)])
def get_leave(db: Session = Depends(get_db2),date: str=None):
    """
    RETURN LEAVES FOR SUMMARY UPDATE - MANUAL TRIGGER - BY DATE
    TRIGGER EVERYTIME AN ADMIN OPENS A ATTENDANCE ON EPORTAL
    """
    try:
        result = leaveService.get_leaves(db,date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")
    
@router.post('/',status_code=200,dependencies=[Depends(verify_key)])
def leave_update(db1: Session = Depends(get_db), db2: Session = Depends(get_db2),start_date:str = None, end_date:str = None):
    """
    AUTOMATICALLY UPDATES SUMMARY FOR LEAVES - TRIGGER USING A PYTHON SCRIPT => SCHEDULED TASK/ CRON
    """
    try:
        result = leaveService.update_summaries(db1,db2,start_date,end_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")

@router.get("/report/",status_code=200,dependencies=[Depends(verify_key)])
def leave_report(db:Session= Depends(get_db2),start_date:str =None, end_date:str =None, employee_id: int = None):
    """
    RETURN - SUMMARY OF LEAVES FOR REPORT
    """
    try:
        result = leaveService.leave_reports(db,start_date,end_date,employee_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")
    
