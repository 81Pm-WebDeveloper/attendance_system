from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.summary_service as summaryService
import services.attendance_service as attendanceService
from db.database import get_db
from dotenv import load_dotenv
import os

router = APIRouter()

@router.post("/", status_code=200)
def insert_summary(db: Session = Depends(get_db)):
    try:
        response = attendanceService.fetch_attendance_today(db)

        data = [
            {
                "employee_id": row["employee_id"],
                "date": row["date"],
                "status": row["status"]
            }
            for row in response
        ]
        
        entries =summaryService.insert_summary(db, data)

        return {"detail": f"Summary logs inserted",
                "data": entries}
    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
