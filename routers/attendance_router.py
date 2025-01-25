from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.attendance_service as attendanceService
from db.database import get_db
from dotenv import load_dotenv
import os


router = APIRouter()
load_dotenv()

@router.post("/",status_code=200)
def insert_attendance(db: Session = Depends(get_db)):
    try:
        device_ip = os.getenv("device_ip")
        port = int(os.getenv("device_port",4370))
        conn = attendanceService.connect_to_device(device_ip,port)
        try:
            response = attendanceService.fetch_logs_for_today(conn,db)
        finally:
            conn.enable_device()
            conn.disconnect()

        return {"detail": "Attendance logs processed successfully."
                ,"date": response}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.get("/")
def get_attendance(
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    status_filter:str = None,
    employee_id_filter: str = None,
    db: Session = Depends(get_db)
):
    return attendanceService.fetch_attendance(db, page, page_size, search_query,date_from,date_to,status_filter,employee_id_filter)
    
@router.get("/today/")
def get_attendance_today(db: Session = Depends(get_db)):
    try:
        return attendanceService.fetch_attendance_today(db)
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")
    
   
 