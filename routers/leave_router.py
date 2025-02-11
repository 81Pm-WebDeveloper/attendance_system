from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.leave_service as leaveService
from db.database2 import get_db2


from config.authentication import verify_key

router = APIRouter()

@router.get("/",status_code=200, dependencies=[Depends(verify_key)],)
def get_leave(db: Session = Depends(get_db2),date: str=None):
    try:
        result = leaveService.get_leaves(db,date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")