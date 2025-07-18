from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.summary_service as summaryService
import services.attendance_service as attendanceService
from db.database import get_db
from db.database2 import get_db2
from schemas.summary import UpdateSummary 
from typing import List
from config.authentication import verify_key
router = APIRouter()

@router.post("/", status_code=200, dependencies=[Depends(verify_key)])
def insert_summary(
    db: Session = Depends(get_db),
    db2: Session = Depends(get_db2),
    start_date = str,
    end_date = str 
    ):
    """
    MANUAL TRIGGER FOR STATUS INSERTS - INCLUDES NO INFO STATUS 
    """
    try:
        response = attendanceService.fetch_attendance_between_dates(db,db2,start_date,end_date)

        data = [
            {
                "employee_id": row["employee_id"],
                "att_id": row["att_id"],
                "date": row["date"],
                "time_in":row["time_in"],
                "time_out":row["time_out"],
                "status": row["status"],
                "checkout_status": row["checkout_status"],
            }
            for row in response 
        ]
        
        entries = summaryService.insert_summary(db, data) 

        return {"detail": f"Summary logs inserted, {entries}"}
    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    
@router.post("/cron/", status_code=200, dependencies=[Depends(verify_key)])
def insert_summary_cron(
    db: Session = Depends(get_db),
    db2: Session = Depends(get_db2),
    start_date = str,
    end_date = str 
    ):
    """
    USED FOR AUTOMATIC STATUS INSERTS - DOESN'T INCLUDE NO INFO STATUS
    USED IN CRON TASKS 
    """
    try:
        response = attendanceService.fetch_attendance_cron(db,db2,start_date,end_date)

        data = [
            {
                "employee_id": row["employee_id"],
                "att_id": row["att_id"],
                "date": row["date"],
                "time_in":row["time_in"],
                "time_out":row["time_out"],
                "status": row["status"],
                "checkout_status": row["checkout_status"],
            }
            for row in response #loop 2
        ]
        
        entries = summaryService.insert_summary(db, data) 

        return {"detail": f"Summary logs inserted, {entries}"}
    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@router.get("/",status_code=200, dependencies=[Depends(verify_key)]) 
def get_summary(
    db1:Session = Depends(get_db),
    db2:Session = Depends(get_db2),
    page: int = 1,
    page_size: int = None,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None):

    """
    DISPLAYS ATTENDANCE
    """
    try:
        return summaryService.fetch_summary(db1,db2,page,page_size,search_query,date_from,date_to,employee_id_filter)
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")

@router.get("/count", dependencies=[Depends(verify_key)])
def fetch_summary_count(
    db: Session = Depends(get_db),
    db2: Session = Depends(get_db2),
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
):
    """
    DISPLAYS ATTENDANCE STATUS COUNTS - USED IN EPORTAL ATTENDANCE SUMMARY
    """
    try:
        summary_data = summaryService.fetch_count(
            db,
            db2,
            search_query,
            date_from,
            date_to,
            employee_id_filter,
        )
        return summary_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")


@router.put("/", status_code=200, dependencies=[Depends(verify_key)])
def update_summary(updates: List[UpdateSummary], db: Session = Depends(get_db)):
    """
    API FOR MANUAL STATUS CHANGES
    """
    try:
        updated_summary = summaryService.update_status(db,updates)
        return {"message": "Summary updated successfully", "summary": updated_summary}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/report/", status_code=200, dependencies=[Depends(verify_key)])
def attendance_report(
    db: Session = Depends(get_db),
    start_date: str = None,
    end_date: str = None,
    employee_id: str = None
):
    """
    GENERATES A REPORT OF ATTENDANCE - USED ALONG WITH LEAVE_REPORT (REPORT - IN EPORTAL)
    """
    try:
        response = summaryService.attendanceReport(db, start_date, end_date, employee_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
