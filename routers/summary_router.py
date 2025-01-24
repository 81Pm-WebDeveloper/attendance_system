from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.summary_service as summaryService
import services.attendance_service as attendanceService
from db.database import get_db
from dotenv import load_dotenv
import os

router = APIRouter()

@router.post("/", status_code=200)
def insert_summary(
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = None,
    search_query: str = None,
    date_filter: str = None,
    status_filter: str = None,
    employee_id_filter: str = None,
    ):
    try:
        response = attendanceService.fetch_attendance(db,page,page_size,search_query,date_filter,status_filter,employee_id_filter)

        data = [
            {
                "employee_id": row.employee_id,
                "date": row.date,
                "status": row.status
            }
            for row in response["records"]
        ]
        
        entries =summaryService.insert_summary(db, data)

        return {"detail": f"Summary logs inserted",
                "data": entries}
    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@router.get("/",status_code=200)
def fetch_summary(
    db:Session = Depends(get_db),
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None):
    try:
        return summaryService.fetch_summary(db,page,page_size,search_query,date_from,date_to,employee_id_filter)
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")
