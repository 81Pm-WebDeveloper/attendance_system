from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.leave_service as leaveService
from db.database2 import get_db2
from db.database import get_db


from config.authentication import verify_key

router = APIRouter()

@router.get("/",status_code=200, dependencies=[Depends(verify_key)],)
def get_leave(db: Session = Depends(get_db2),date: str=None):
    try:
        result = leaveService.get_leaves(db,date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")
    
@router.post('/',status_code=200,dependencies=[Depends(verify_key)])
def leave_update(db1: Session = Depends(get_db), db2: Session = Depends(get_db2),start_date:str = None, end_date:str = None):
    try:
        result = leaveService.update_summaries(db1,db2,start_date,end_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")

@router.get("/report/",status_code=200,dependencies=[Depends(verify_key)])
def leave_report(db:Session= Depends(get_db2),start_date:str =None, end_date:str =None, employee_id: int = None):
    try:
        result = leaveService.leave_reports(db,start_date,end_date,employee_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")
    
